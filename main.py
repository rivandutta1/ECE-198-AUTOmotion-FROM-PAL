#! .venv/bin/python

"""AutoMotion: independent 60 Hz UI and asynchronous camera/pose/Arduino work.

OpenCV HighGUI's rendering cadence is a *target*, not a screen vsync guarantee.
Camera and inference can run at 24-30 FPS without freezing interactive controls.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import queue
import sys
import threading
import time

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "Auto-motion"))

from src.app_modes import EXERCISES, SIDES, EXERCISE_NAMES, create_monitor, evaluate_monitor
from src.arm_exercises import Feedback
from src.arm_ui import WINDOW_TITLE, WIDTH, HEIGHT, draw_screen, hit_test
from src.serial_link import SerialLink, find_arduino_port

TARGET_UI_HZ = 60.0


def camera_setup(camera_index: int, width: int = 1280,
                 height: int = 720, camera_fps: int = 30):
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        cap.release()
        raise RuntimeError("Camera unavailable: try CHANGE CAMERA or check macOS permissions")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_FPS, camera_fps)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap


def make_link(port):
    candidate = port or find_arduino_port()
    if not candidate:
        return SerialLink(None), "No unambiguous Arduino USB port found"
    try:
        link = SerialLink(candidate)
        return link, f"Arduino ready: {candidate}"
    except Exception as exc:
        return SerialLink(None), f"Could not connect to {candidate}: {exc}"


def tracking_frame(frame, max_width: int):
    """Keep a sharp preview; only reduce resolution for pose inference."""
    h, w = frame.shape[:2]
    if w <= max_width:
        return frame, w, h
    s = max_width / float(w)
    tw, th = max(1, round(w*s)), max(1, round(h*s))
    return cv2.resize(frame, (tw, th), interpolation=cv2.INTER_AREA), tw, th


def idle_feedback(message="Starting camera and pose tracker..."):
    return Feedback("UNKNOWN", message, "CAL", 0, 0, "READY")


@dataclass(frozen=True)
class Snapshot:
    frame: np.ndarray
    landmarks: object
    feedback: Feedback
    exercise: str
    side: str
    arduino_connected: bool
    camera_fps: float
    error: str | None = None


class CameraWorker:
    """Owns ALL blocking video, MediaPipe and serial operations, off the UI thread.

    The main thread owns all OpenCV windows and mouse/keyboard handling.
    A lock protects only a short immutable snapshot reference swap; no camera
    reads, inference, serial operations, or rendering run under that lock.
    """
    def __init__(self, args):
        self.args = args
        self._lock = threading.Lock()
        self._actions = queue.SimpleQueue()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="automotion-camera", daemon=True)
        placeholder = np.full((720, 1280, 3), (24, 22, 21), dtype=np.uint8)
        self._snapshot = Snapshot(placeholder, None, idle_feedback(),
                                  args.exercise, args.side, False, 0.0)

    def start(self):
        self._thread.start()

    def send(self, action: str):
        self._actions.put(action)

    def snapshot(self) -> Snapshot:
        with self._lock:
            return self._snapshot

    def _publish(self, snapshot):
        with self._lock:
            self._snapshot = snapshot

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=3.0)

    def _run(self):
        cap = None
        tracker = None
        link = None
        a = self.args
        exercise, side, camera_index = a.exercise, a.side, a.camera
        monitor = create_monitor(exercise, side)
        started = time.monotonic()
        previous_ts = -1
        last_send = -1.0
        previous_frame_time = None
        camera_fps = 0.0
        latest_frame = self.snapshot().frame
        latest_landmarks = None
        result = idle_feedback()
        error = None
        try:
            from src.vision import VisionTracker
            try:
                cap = camera_setup(camera_index, a.camera_width, a.camera_height, a.camera_fps)
            except (RuntimeError, cv2.error):
                if camera_index == 0:
                    raise
                print(f"Camera {camera_index} unavailable; trying camera 0", flush=True)
                camera_index = 0
                cap = camera_setup(camera_index, a.camera_width, a.camera_height, a.camera_fps)
            tracker = VisionTracker(ROOT / "models" / f"pose_landmarker_{a.model}.task")
            link, message = make_link(a.port)
            print(message, flush=True)
            while not self._stop.is_set():
                while True:
                    try:
                        action = self._actions.get_nowait()
                    except queue.Empty:
                        break
                    if action.startswith("mode:"):
                        mode = action.split(":",1)[1]
                        if mode in EXERCISES and mode != exercise:
                            exercise = mode
                            monitor = create_monitor(exercise, side)
                            latest_landmarks = None
                            result = idle_feedback("Press CALIBRATE for the new exercise")
                            last_send = -1.0
                    elif action.startswith("side:"):
                        new_side = action.split(":",1)[1]
                        if new_side in SIDES and new_side != side:
                            side = new_side
                            monitor = create_monitor(exercise, side)
                            latest_landmarks = None
                            result = idle_feedback("Press CALIBRATE for the selected arm")
                            last_send = -1.0
                    elif action == "calibrate":
                        monitor.start_calibration()
                    elif action == "reset":
                        monitor.reset_reps()
                    elif action == "arduino":
                        if link is not None:
                            link.close()
                        link, message = make_link(a.port)
                        print(message, flush=True)
                    elif action == "camera":
                        for i in range(1,4):
                            candidate = (camera_index + i) % 4
                            try:
                                new_cap = camera_setup(candidate, a.camera_width,
                                                       a.camera_height, a.camera_fps)
                                ok, candidate_frame = new_cap.read()
                                if not ok:
                                    new_cap.release()
                                    continue
                            except (RuntimeError, cv2.error):
                                continue
                            cap.release()
                            cap = new_cap
                            camera_index = candidate
                            monitor = create_monitor(exercise, side)
                            result = idle_feedback("Camera changed; press CALIBRATE")
                            latest_frame = candidate_frame
                            latest_landmarks = None
                            previous_frame_time = None
                            camera_fps = 0.0
                            print(f"Camera switched to {candidate}")
                            break
                        else:
                            print("No other usable webcam found")

                ok, frame = cap.read()
                if not ok:
                    raise RuntimeError("Camera stopped delivering frames")
                now = time.monotonic()
                if previous_frame_time is not None and now > previous_frame_time:
                    measured_fps = min(90.0, 1.0/(now-previous_frame_time))
                    camera_fps = measured_fps if not camera_fps else (.88*camera_fps+.12*measured_fps)
                previous_frame_time = now
                ms = max(int((now-started)*1000), previous_ts+1)
                previous_ts = ms

                pose_frame, track_w, track_h = tracking_frame(frame, a.tracking_width)
                landmarks = tracker.process(pose_frame, ms)
                result = evaluate_monitor(monitor, exercise, side,
                                          landmarks, track_w, track_h, ms)
                latest_frame = frame
                latest_landmarks = landmarks
                if a.debug_tracking:
                    diagnostic = (exercise, side, result.status, result.issue, result.message)
                    if getattr(self, "_last_diagnostic", None) != diagnostic:
                        print(f"{ms/1000:.1f}s {exercise}/{side}: {result.status} - {result.message}")
                        self._last_diagnostic = diagnostic
                if now - last_send >= .20 and link is not None:
                    try:
                        link.send_feedback(exercise.upper(), result.status, result.issue,
                                           result.reps)
                    except Exception as exc:
                        print(f"Arduino disconnected: {exc}", flush=True)
                        link.close()
                    last_send = now
                self._publish(Snapshot(latest_frame, latest_landmarks, result,
                                       exercise, side, link is not None and link.connection is not None,
                                       camera_fps))
        except Exception as exc:
            error = str(exc)
            print("AutoMotion camera worker:", error, flush=True)
            self._publish(Snapshot(latest_frame, None,
                                   Feedback("UNKNOWN", error, "TRACK", 0, 0, "WAITING"),
                                   exercise, side, False, camera_fps, error))
        finally:
            if link is not None:
                link.close()
            if tracker is not None:
                tracker.close()
            if cap is not None:
                cap.release()


def main(argv=None):
    parser = argparse.ArgumentParser(description="AutoMotion fitness feedback")
    parser.add_argument("--exercise", choices=EXERCISES, default="curl")
    parser.add_argument("--side", choices=SIDES, default="right")
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--model", choices=("lite","full"), default="lite")
    parser.add_argument("--port", help="Arduino USB port (auto-detected when omitted)")
    parser.add_argument("--camera-width", type=int, default=1280)
    parser.add_argument("--camera-height", type=int, default=720)
    parser.add_argument("--camera-fps", type=int, default=30)
    parser.add_argument("--tracking-width", type=int, default=960)
    parser.add_argument("--ui-hz", type=float, default=TARGET_UI_HZ)
    parser.add_argument("--debug-tracking", action="store_true")
    args = parser.parse_args(argv)
    if args.camera_width < 320 or args.camera_height < 240:
        parser.error("Camera must be at least 320x240")
    if args.camera_fps < 1 or args.camera_fps > 120:
        parser.error("Camera fps must be from 1 to 120")
    if args.tracking_width < 320:
        parser.error("Tracking width must be at least 320")
    if not 10 <= args.ui_hz <= 120:
        parser.error("UI refresh target must be from 10 to 120 Hz")
    cv2.setUseOptimized(True)
    worker = CameraWorker(args)
    mirrored = True
    pending_clicks = []
    window_created = False
    try:
        def clicked(event, x, y, flags, user_data):
            if event == cv2.EVENT_LBUTTONUP:
                action = hit_test(x, y)
                if action:
                    pending_clicks.append(action)

        # All HighGUI calls stay on the main thread, which matters on macOS.
        cv2.namedWindow(WINDOW_TITLE, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(WINDOW_TITLE, WIDTH, HEIGHT)
        cv2.setMouseCallback(WINDOW_TITLE, clicked)
        window_created = True
        worker.start()
        frame_interval = 1.0 / args.ui_hz
        next_frame_at = time.perf_counter()
        previous_ui_frame = None
        ui_fps = 0.0
        shortcuts = {
            ord("1"):"mode:curl", ord("2"):"mode:pushdown",
            
            ord("l"):"side:left", ord("L"):"side:left",
            ord("r"):"side:right", ord("R"):"side:right",
            ord("c"):"calibrate", ord("C"):"calibrate",
            ord("m"):"mirror", ord("M"):"mirror",
            ord("q"):"quit", ord("Q"):"quit", 27:"quit",
        }
        running = True
        while running:
            started = time.perf_counter()
            if previous_ui_frame is not None:
                elapsed = max(1e-6, started-previous_ui_frame)
                measured = min(180.0, 1.0/elapsed)
                ui_fps = measured if not ui_fps else (.85*ui_fps+.15*measured)
            previous_ui_frame = started
            snap = worker.snapshot()
            h,w = snap.frame.shape[:2]
            canvas = draw_screen(snap.frame, snap.landmarks, snap.side, snap.exercise,
                                 snap.feedback, snap.arduino_connected, fps=ui_fps,
                                 mirrored=mirrored, camera_resolution=(w,h),
                                 camera_fps=snap.camera_fps)
            cv2.imshow(WINDOW_TITLE, canvas)
            key = cv2.waitKey(1) & 0xFF
            try:
                if cv2.getWindowProperty(WINDOW_TITLE, cv2.WND_PROP_VISIBLE) < 1:
                    break
            except cv2.error:
                break
            actions = pending_clicks[:]
            pending_clicks.clear()
            if key in shortcuts:
                actions.append(shortcuts[key])
            for action in actions:
                if action == "quit":
                    running = False
                elif action == "mirror":
                    mirrored = not mirrored
                else:
                    worker.send(action)

            next_frame_at += frame_interval
            remaining = next_frame_at - time.perf_counter()
            if remaining > 0:
                time.sleep(remaining)
            elif remaining < -frame_interval:
                next_frame_at = time.perf_counter()
    finally:
        worker.stop()
        if window_created:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
