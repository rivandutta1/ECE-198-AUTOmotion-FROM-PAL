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
import threading
import time

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent

from app_modes import EXERCISES, SIDES, create_monitor, evaluate_monitor
from arm_exercises import Feedback
from arm_ui import WINDOW_TITLE, WIDTH, HEIGHT, draw_screen, hit_test
from serial_link import SerialLink, find_arduino_port

TARGET_UI_HZ = 60.0
SERIAL_SEND_INTERVAL_S = 0.20
CAMERA_SLOTS = 4  # the CAMERA button cycles through indexes 0-3


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
    """Everything the UI thread needs to draw one frame."""
    frame: np.ndarray
    landmarks: object
    feedback: Feedback
    exercise: str
    side: str
    arduino_connected: bool


class CameraWorker:
    """Owns ALL blocking video, MediaPipe and serial operations, off the UI thread.

    The main thread owns all OpenCV windows and mouse/keyboard handling.
    It talks to this worker only through send(action) and snapshot().
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
                                  args.exercise, args.side, False)
        self._last_diagnostic = None

    # --- Called from the UI thread -------------------------------------
    def start(self):
        self._thread.start()

    def send(self, action: str):
        self._actions.put(action)

    def snapshot(self) -> Snapshot:
        with self._lock:
            return self._snapshot

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=3.0)

    # --- Worker thread only --------------------------------------------
    def _publish(self, snapshot):
        with self._lock:
            self._snapshot = snapshot

    def _open_camera(self, index):
        a = self.args
        return camera_setup(index, a.camera_width, a.camera_height, a.camera_fps)

    def _open_first_camera(self):
        """Open --camera, falling back to camera 0 if it is unavailable."""
        try:
            return self._open_camera(self.camera_index)
        except (RuntimeError, cv2.error):
            if self.camera_index == 0:
                raise
            print(f"Camera {self.camera_index} unavailable; trying camera 0", flush=True)
            self.camera_index = 0
            return self._open_camera(0)

    def _switch_to_next_camera(self):
        """Try the next camera indexes in turn; keep the current one if none work."""
        for step in range(1, CAMERA_SLOTS):
            candidate = (self.camera_index + step) % CAMERA_SLOTS
            try:
                new_cap = self._open_camera(candidate)
                ok, first_frame = new_cap.read()
                if not ok:
                    new_cap.release()
                    continue
            except (RuntimeError, cv2.error):
                continue
            self.cap.release()
            self.cap = new_cap
            self.camera_index = candidate
            self.monitor = create_monitor(self.exercise, self.side)
            self.latest_frame = first_frame
            print(f"Camera switched to {candidate}")
            return
        print("No other usable webcam found")

    def _connect_arduino(self):
        if self.link is not None:
            self.link.close()
        self.link, message = make_link(self.args.port)
        print(message, flush=True)

    def _handle_action(self, action: str):
        """Apply one UI action (button click or key press)."""
        kind, _, value = action.partition(":")
        if kind == "mode" and value in EXERCISES and value != self.exercise:
            self.exercise = value
            self.monitor = create_monitor(self.exercise, self.side)
            self.last_send = -1.0  # tell the Arduino right away
        elif kind == "side" and value in SIDES and value != self.side:
            self.side = value
            self.monitor = create_monitor(self.exercise, self.side)
            self.last_send = -1.0
        elif action == "calibrate":
            self.monitor.start_calibration()
        elif action == "reset":
            self.monitor.reset_reps()
        elif action == "arduino":
            self._connect_arduino()
        elif action == "camera":
            self._switch_to_next_camera()

    def _handle_pending_actions(self):
        while True:
            try:
                action = self._actions.get_nowait()
            except queue.Empty:
                return
            self._handle_action(action)

    def _print_diagnostic(self, ms, result):
        diagnostic = (self.exercise, self.side, result.status, result.issue, result.message)
        if diagnostic != self._last_diagnostic:
            print(f"{ms/1000:.1f}s {self.exercise}/{self.side}: {result.status} - {result.message}")
            self._last_diagnostic = diagnostic

    def _send_to_arduino(self, now, result):
        """Send at most one packet every SERIAL_SEND_INTERVAL_S seconds."""
        if self.link is None or now - self.last_send < SERIAL_SEND_INTERVAL_S:
            return
        try:
            self.link.send_feedback(self.exercise.upper(), result.status, result.issue,
                                    result.reps)
        except Exception as exc:
            print(f"Arduino disconnected: {exc}", flush=True)
            self.link.close()
        self.last_send = now

    def _run(self):
        a = self.args
        self.exercise, self.side, self.camera_index = a.exercise, a.side, a.camera
        self.monitor = create_monitor(self.exercise, self.side)
        self.cap = None
        self.link = None
        self.last_send = -1.0
        self.latest_frame = self.snapshot().frame
        tracker = None
        started = time.monotonic()
        previous_ts = -1
        try:
            from vision import VisionTracker  # imported here so tests can run without MediaPipe
            self.cap = self._open_first_camera()
            tracker = VisionTracker(ROOT / "models" / f"pose_landmarker_{a.model}.task")
            self._connect_arduino()
            while not self._stop.is_set():
                self._handle_pending_actions()

                ok, frame = self.cap.read()
                if not ok:
                    raise RuntimeError("Camera stopped delivering frames")
                now = time.monotonic()
                # MediaPipe VIDEO mode needs strictly increasing timestamps.
                ms = max(int((now-started)*1000), previous_ts+1)
                previous_ts = ms

                pose_frame, track_w, track_h = tracking_frame(frame, a.tracking_width)
                landmarks = tracker.process(pose_frame, ms)
                result = evaluate_monitor(self.monitor, landmarks, track_w, track_h, ms)
                self.latest_frame = frame
                if a.debug_tracking:
                    self._print_diagnostic(ms, result)
                self._send_to_arduino(now, result)
                connected = self.link is not None and self.link.connection is not None
                self._publish(Snapshot(frame, landmarks, result,
                                       self.exercise, self.side, connected))
        except Exception as exc:
            error = str(exc)
            print("AutoMotion camera worker:", error, flush=True)
            self._publish(Snapshot(self.latest_frame, None,
                                   Feedback("UNKNOWN", error, "TRACK", 0, 0, "WAITING"),
                                   self.exercise, self.side, False))
        finally:
            if self.link is not None:
                self.link.close()
            if tracker is not None:
                tracker.close()
            if self.cap is not None:
                self.cap.release()


KEY_SHORTCUTS = {
    ord("1"): "mode:curl", ord("2"): "mode:pushdown",
    ord("l"): "side:left", ord("L"): "side:left",
    ord("r"): "side:right", ord("R"): "side:right",
    ord("c"): "calibrate", ord("C"): "calibrate",
    ord("m"): "mirror", ord("M"): "mirror",
    ord("q"): "quit", ord("Q"): "quit", 27: "quit",  # 27 = Esc
}


def fit_to_window(canvas, window_rect):
    """Scale the dashboard to the size the window actually shows it at.

    OpenCV's window shrinks or stretches an image with rough sampling, which
    makes text jagged whenever the window isn't exactly WIDTH x HEIGHT (e.g. on
    a scaled laptop screen). Resizing it ourselves with a smooth filter keeps
    the text clean. Returns the image and the factor that turns a click on it
    back into dashboard coordinates.
    """
    _, _, w, h = window_rect
    if w <= 0 or h <= 0:
        return canvas, 1.0
    # Keep the dashboard's shape so the window's own fitting can't drift.
    scale = min(w / WIDTH, h / HEIGHT)
    size = (max(1, round(WIDTH * scale)), max(1, round(HEIGHT * scale)))
    if size == (WIDTH, HEIGHT):
        return canvas, 1.0
    smooth = cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC
    return cv2.resize(canvas, size, interpolation=smooth), WIDTH / size[0]


def window_image_rect():
    """(x, y, width, height) of the image area inside the window, or zeros."""
    try:
        return cv2.getWindowImageRect(WINDOW_TITLE)
    except cv2.error:
        return (0, 0, 0, 0)


def parse_args(argv=None):
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
    return args


def main(argv=None):
    args = parse_args(argv)
    cv2.setUseOptimized(True)
    worker = CameraWorker(args)
    mirrored = True
    pending_clicks = []
    click_scale = 1.0  # window pixels -> dashboard pixels (see fit_to_window)
    window_created = False
    try:
        def clicked(event, x, y, flags, user_data):
            if event == cv2.EVENT_LBUTTONUP:
                action = hit_test(round(x * click_scale), round(y * click_scale))
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
        running = True
        while running:
            snap = worker.snapshot()
            canvas = draw_screen(snap.frame, snap.landmarks, snap.side, snap.exercise,
                                 snap.feedback, snap.arduino_connected, mirrored=mirrored)
            canvas, click_scale = fit_to_window(canvas, window_image_rect())
            cv2.imshow(WINDOW_TITLE, canvas)
            key = cv2.waitKey(1) & 0xFF
            try:
                if cv2.getWindowProperty(WINDOW_TITLE, cv2.WND_PROP_VISIBLE) < 1:
                    break
            except cv2.error:
                break
            actions = pending_clicks[:]
            pending_clicks.clear()
            if key in KEY_SHORTCUTS:
                actions.append(KEY_SHORTCUTS[key])
            for action in actions:
                if action == "quit":
                    running = False
                elif action == "mirror":
                    mirrored = not mirrored
                else:
                    worker.send(action)

            # Sleep until the next UI frame; if far behind, don't try to catch up.
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
