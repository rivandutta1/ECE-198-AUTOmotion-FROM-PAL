#! .venv/bin/python

"""AutoMotion: a 60 Hz Qt window plus a background camera/pose/Arduino thread.

The window (DashboardWindow) only draws the latest Snapshot and turns clicks
and keys into actions; camera and inference can run at 24-30 FPS without
freezing interactive controls.
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
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget

ROOT = Path(__file__).resolve().parent

import history
from app_modes import EXERCISES, SIDES, create_monitor, evaluate_monitor
from arm_exercises import Feedback
from arm_ui import (BG, WINDOW_TITLE, WIDTH, HEIGHT, hit_test, paint_dashboard,
                    paint_history, qt_app)
from serial_link import SerialLink, find_arduino_port, parse_press_packet

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
        self.history_file = Path(getattr(args, "history_file", None) or history.DEFAULT_PATH)
        self._press_saved = {}  # (session, exercise) -> (reps, rom) last written

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
            self._save_set()
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
            self._save_set()
            self.exercise = value
            self.monitor = create_monitor(self.exercise, self.side)
            self.last_send = -1.0  # tell the Arduino right away
        elif kind == "side" and value in SIDES and value != self.side:
            self._save_set()
            self.side = value
            self.monitor = create_monitor(self.exercise, self.side)
            self.last_send = -1.0
        elif action == "calibrate":
            self._save_set()  # a fresh calibration also clears the reps
            self.monitor.start_calibration()
        elif action == "reset":
            self._save_set()
            self.monitor.reset_reps()
        elif action == "arduino":
            self._connect_arduino()
        elif action == "camera":
            self._switch_to_next_camera()

    def _save_set(self):
        """Write the current camera set to the history file (if it has reps)."""
        if self.monitor.reps == 0:
            return
        try:
            history.save_set(self.history_file, self.exercise, self.side,
                             self.monitor.reps, self.monitor.bad_reps)
        except OSError as exc:
            print(f"Could not save set to {self.history_file}: {exc}", flush=True)

    def _save_press_totals(self):
        """Save shoulder/chest press totals the Arduino has sent (P lines)."""
        if self.link is None:
            return
        try:
            lines = self.link.read_lines()
        except Exception as exc:
            print(f"Arduino disconnected: {exc}", flush=True)
            self.link.close()
            return
        for line in lines:
            totals = parse_press_packet(line)
            if totals is None or (totals.reps == 0 and totals.rom_cm == 0):
                continue
            key, value = (totals.session, totals.exercise), (totals.reps, totals.rom_cm)
            if self._press_saved.get(key) == value:
                continue  # already saved (e.g. resent on reconnect)
            try:
                history.save_press(self.history_file, totals.session, totals.exercise,
                                   totals.reps, totals.rom_cm)
                self._press_saved[key] = value
            except OSError as exc:
                print(f"Could not save press totals to {self.history_file}: {exc}", flush=True)

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
                self._save_press_totals()

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
            self._save_set()  # the set in progress when the app closes
            if self.link is not None:
                self.link.close()
            if tracker is not None:
                tracker.close()
            if self.cap is not None:
                self.cap.release()


KEY_SHORTCUTS = {  # typed character (lower case) -> action
    "1": "mode:curl", "2": "mode:pushdown",
    "l": "side:left", "r": "side:right",
    "c": "calibrate", "m": "mirror", "q": "quit", "h": "history",
}


class DashboardWindow(QWidget):
    """The app window: paints the worker's latest Snapshot ui_hz times a second
    and turns clicks and key presses into actions.

    Two pages: "live" (the dashboard) and "history" (saved sets and press
    sessions from the history file). Pages are laid out in WIDTH x HEIGHT
    units; the painter is scaled to the window (keeping its shape), so Qt draws
    them sharp at any size and on high-DPI screens.
    """
    def __init__(self, worker, ui_hz: float = TARGET_UI_HZ,
                 history_file: Path = history.DEFAULT_PATH):
        super().__init__()
        self.worker = worker
        self.mirrored = True
        self.page = "live"
        self.history_file = Path(history_file)
        self._history_cache = (None, [], [])  # (file change time, camera sets, presses)
        self.setWindowTitle(WINDOW_TITLE)
        self.setMinimumSize(WIDTH // 3, HEIGHT // 3)
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.PreciseTimer)
        self._timer.timeout.connect(self.update)  # update() schedules a repaint
        self._timer.start(max(1, round(1000 / ui_hz)))

    def _placement(self):
        """(scale, x offset, y offset) that fits the dashboard in the window."""
        scale = min(self.width() / WIDTH, self.height() / HEIGHT)
        return (scale, (self.width() - WIDTH * scale) / 2,
                (self.height() - HEIGHT * scale) / 2)

    def _saved_history(self):
        """(camera sets, press sessions), re-read only when the file changes."""
        try:
            changed = self.history_file.stat().st_mtime_ns
        except OSError:
            changed = None
        if changed != self._history_cache[0]:
            entries = history.load(self.history_file) if changed else []
            self._history_cache = (
                changed,
                [e for e in entries if isinstance(e, history.CameraSet)],
                [e for e in entries if isinstance(e, history.PressSession)])
        return self._history_cache[1:]

    def _file_label(self):
        try:
            return str(self.history_file.resolve().relative_to(ROOT))
        except ValueError:
            return str(self.history_file)

    def paintEvent(self, event):
        painter = QPainter(self)
        try:
            painter.fillRect(self.rect(), QColor(*BG))  # bars around the page
            scale, dx, dy = self._placement()
            painter.translate(dx, dy)
            painter.scale(scale, scale)
            if self.page == "history":
                camera_sets, press_sessions = self._saved_history()
                paint_history(painter, camera_sets, press_sessions, self._file_label())
            else:
                snap = self.worker.snapshot()
                paint_dashboard(painter, snap.frame, snap.landmarks, snap.side, snap.exercise,
                                snap.feedback, snap.arduino_connected, mirrored=self.mirrored)
        finally:
            painter.end()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        scale, dx, dy = self._placement()
        position = event.position()
        action = hit_test(int((position.x() - dx) / scale), int((position.y() - dy) / scale),
                          self.page)
        if action:
            self.handle(action)

    def keyPressEvent(self, event):
        if self.page == "history":
            # Only leaving the page or quitting work here; live controls are hidden.
            key = event.text().lower()
            action = ("back" if event.key() == Qt.Key_Escape or key == "h" else
                      "quit" if key == "q" else None)
        else:
            action = ("quit" if event.key() == Qt.Key_Escape else
                      KEY_SHORTCUTS.get(event.text().lower()))
        if action:
            self.handle(action)

    def handle(self, action: str):
        if action == "quit":
            self.close()
        elif action in ("history", "back"):
            self.page = "history" if action == "history" else "live"
            self.update()
        elif action == "mirror":
            self.mirrored = not self.mirrored
            self.update()
        else:
            self.worker.send(action)


def initial_window_size(screen_width: int, screen_height: int):
    """1600x900, shrunk (keeping its shape) to fit 90% of the screen."""
    scale = min(1.0, .9 * screen_width / WIDTH, .9 * screen_height / HEIGHT)
    return round(WIDTH * scale), round(HEIGHT * scale)


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
    parser.add_argument("--history-file", type=Path, default=history.DEFAULT_PATH,
                        help="where sets and press totals are saved (default: data/history.txt)")
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
    app = qt_app()
    worker = CameraWorker(args)
    window = DashboardWindow(worker, args.ui_hz, args.history_file)
    screen = app.primaryScreen().availableGeometry()
    window.resize(*initial_window_size(screen.width(), screen.height()))
    worker.start()
    window.show()
    try:
        app.exec()  # returns when the window is closed (Exit, Q, Esc or the title bar)
    finally:
        worker.stop()


if __name__ == "__main__":
    main()
