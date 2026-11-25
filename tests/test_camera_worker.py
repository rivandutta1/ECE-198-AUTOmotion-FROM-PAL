"""main.py: the CameraWorker thread and UI helpers, with a fake camera, tracker and Arduino."""
import sys
import threading
import time
import types
from types import SimpleNamespace

import numpy as np
import pytest

import main
from main import TARGET_UI_HZ, CameraWorker, Snapshot, tracking_frame, idle_feedback
from arm_ui import draw_screen, WIDTH, HEIGHT


def test_target_ui_rate_is_60_hz():
    assert TARGET_UI_HZ == 60.0


def test_tracking_downscale_preserves_aspect_ratio():
    source = np.zeros((720,1280,3), dtype=np.uint8)
    result, w, h = tracking_frame(source, 960)
    assert (w,h) == (960,540)
    assert result.shape == (540,960,3)
    assert tracking_frame(source, 1920)[0] is source


def test_worker_starts_with_nonblocking_snapshot():
    args = SimpleNamespace(exercise="curl", side="right")
    worker = CameraWorker(args)
    s = worker.snapshot()
    assert isinstance(s, Snapshot)
    assert s.feedback.status == "UNKNOWN"
    assert s.frame.shape == (720,1280,3)


def test_ui_renders_idle_feedback():
    sample = np.zeros((720,1280,3), dtype=np.uint8)
    canvas = draw_screen(sample, None, "right", "curl", idle_feedback(), False)
    assert canvas.shape == (HEIGHT, WIDTH, 3)


@pytest.mark.parametrize("camera_one_available", [True, False])
def test_worker_background_operations_without_real_webcam(monkeypatch, camera_one_available,
                                                          tmp_path):
    history_file = tmp_path / "history.txt"
    closed = threading.Event()
    sent_feedback = []
    camera_attempts = []

    class FakeCapture:
        def read(self):
            time.sleep(.025)  # 40 simulated camera FPS
            return True, np.zeros((240, 320, 3), dtype=np.uint8)
        def release(self):
            closed.set()

    class FakeTracker:
        def __init__(self, path):
            pass
        def process(self, frame, ms):
            return None
        def close(self):
            pass

    class FakeLink:
        connection = object()
        def send_feedback(self, *args):
            sent_feedback.append(args)
        def read_lines(self):
            return []
        def close(self):
            pass

    monkeypatch.setitem(sys.modules, "vision", types.SimpleNamespace(VisionTracker=FakeTracker))
    def open_camera(index, *_args):
        camera_attempts.append(index)
        if index == 1 and not camera_one_available:
            raise RuntimeError("Camera unavailable")
        return FakeCapture()

    monkeypatch.setattr(main, "camera_setup", open_camera)
    monkeypatch.setattr(main, "make_link", lambda port: (FakeLink(), "test USB"))
    args = types.SimpleNamespace(
        exercise="curl", side="right", camera=1,
        camera_width=320, camera_height=240, camera_fps=24,
        tracking_width=960, model="lite", port=None, debug_tracking=False,
        history_file=history_file,
    )
    worker = main.CameraWorker(args)
    worker.start()
    try:
        time.sleep(.08)
        assert worker.snapshot().frame.shape == (240,320,3)
        worker.send("mode:pushdown")
        worker.send("side:left")
        end = time.monotonic() + 1
        while time.monotonic() < end:
            snapshot = worker.snapshot()
            if snapshot.exercise == "pushdown" and snapshot.side == "left":
                break
            time.sleep(.01)
        assert snapshot.exercise == "pushdown"
        assert snapshot.side == "left"
        assert snapshot.feedback.status == "UNKNOWN"
        assert camera_attempts == ([1] if camera_one_available else [1, 0])
        assert snapshot.arduino_connected
        assert sent_feedback[0] == ("CURL", "UNKNOWN", "TRACK", 0)
        assert sent_feedback[-1] == ("PUSHDOWN", "UNKNOWN", "TRACK", 0)
        # The main thread can get snapshots immediately, despite slow read.
        t0 = time.perf_counter()
        worker.snapshot()
        assert time.perf_counter() - t0 < .025
    finally:
        worker.stop()
    assert closed.is_set()


class FakeWorker:
    def __init__(self):
        self.sent = []
        self._snapshot = CameraWorker(SimpleNamespace(exercise="curl", side="right")).snapshot()
    def snapshot(self):
        return self._snapshot
    def send(self, action):
        self.sent.append(action)


def test_window_turns_clicks_and_keys_into_actions():
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest
    from arm_ui import controls
    app = main.qt_app()
    worker = FakeWorker()
    window = main.DashboardWindow(worker)
    window.resize(WIDTH // 2, HEIGHT // 2 + 100)  # letterboxed: 50 px bars top and bottom
    window.show()
    calibrate = next(b for b in controls() if b.action == "calibrate")
    x1, y1, x2, y2 = calibrate.rect
    QTest.mouseClick(window, Qt.LeftButton, pos=QPoint((x1 + x2) // 4, (y1 + y2) // 4 + 50))
    QTest.keyClick(window, Qt.Key_2)
    QTest.keyClick(window, Qt.Key_L)
    assert worker.sent == ["calibrate", "mode:pushdown", "side:left"]
    QTest.keyClick(window, Qt.Key_M)
    assert window.mirrored is False and len(worker.sent) == 3
    assert not window.grab().isNull()  # paints without errors
    QTest.keyClick(window, Qt.Key_Escape)
    app.processEvents()
    assert not window.isVisible()


def test_initial_window_fits_the_screen():
    assert main.initial_window_size(2560, 1440) == (WIDTH, HEIGHT)
    width, height = main.initial_window_size(1504, 1003)
    assert width <= round(1504 * .9) and abs(width / height - WIDTH / HEIGHT) < .01



def worker_with_history(tmp_path):
    worker = CameraWorker(SimpleNamespace(exercise="curl", side="right",
                                          history_file=tmp_path / "history.txt"))
    worker.exercise, worker.side = "curl", "right"
    worker.monitor = main.create_monitor("curl", "right")
    worker.link = None
    return worker


def test_a_set_is_saved_when_it_ends(tmp_path):
    import history
    worker = worker_with_history(tmp_path)
    worker._handle_action("mode:pushdown")  # no reps yet: nothing saved
    assert history.load(worker.history_file) == []
    worker.monitor.reps, worker.monitor.bad_reps = 6, 1
    worker._handle_action("reset")
    worker.monitor.reps = 4
    worker._handle_action("side:left")
    saved = [(e.exercise, e.arm, e.reps, e.flagged) for e in history.load(worker.history_file)]
    assert saved == [("Tricep pushdown", "right", 4, 0), ("Tricep pushdown", "right", 6, 1)]


def test_press_totals_from_the_arduino_are_saved_once_per_change(tmp_path):
    import history
    worker = worker_with_history(tmp_path)
    class Link:
        connection = object()
        incoming = [["Switched modes", "P,9,CHEST,0,0", "P,9,CHEST,1,20"],
                    ["P,9,CHEST,1,20"], ["P,9,CHEST,2,31"]]
        def read_lines(self):
            return self.incoming.pop(0)
    worker.link = Link()
    for _ in range(3):
        worker._save_press_totals()
    lines = worker.history_file.read_text().splitlines()
    assert len(lines) == 1 and "2 reps | max ROM 31 cm | session 9" in lines[0]


def test_window_opens_and_closes_the_history_page(tmp_path):
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest
    import arm_ui
    import history
    path = tmp_path / "history.txt"
    history.save_set(path, "curl", "right", 7, 0)
    main.qt_app()
    worker = FakeWorker()
    window = main.DashboardWindow(worker, history_file=path)
    window.resize(WIDTH // 2, HEIGHT // 2)
    window.show()
    QTest.keyClick(window, Qt.Key_H)
    assert window.page == "history"
    assert not window.grab().isNull()  # paints the saved set
    QTest.keyClick(window, Qt.Key_1)  # live shortcuts are ignored here
    assert worker.sent == []
    x1, y1, x2, y2 = arm_ui.history_controls()[0].rect
    QTest.mouseClick(window, Qt.LeftButton, pos=QPoint((x1 + x2) // 4, (y1 + y2) // 4))
    assert window.page == "live"
    window.close()
