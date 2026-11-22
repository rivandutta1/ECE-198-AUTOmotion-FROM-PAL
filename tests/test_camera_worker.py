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
def test_worker_background_operations_without_real_webcam(monkeypatch, camera_one_available):
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


def test_dashboard_is_resized_to_the_window_and_clicks_map_back():
    canvas = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    # Window shows the image at its own size: nothing to do.
    same, scale = main.fit_to_window(canvas, (0, 0, WIDTH, HEIGHT))
    assert same is canvas and scale == 1.0
    # Smaller window (e.g. a 150%-scaled laptop screen): we shrink it ourselves.
    small, scale = main.fit_to_window(canvas, (0, 0, 1504, 846))
    assert small.shape == (846, 1504, 3)
    assert round(1504 * scale) == WIDTH
    # The dashboard keeps its shape even if the window's doesn't match.
    wide, _ = main.fit_to_window(canvas, (0, 0, 1504, 1000))
    assert wide.shape[:2] == (846, 1504)
    # No window yet: leave it alone.
    untouched, scale = main.fit_to_window(canvas, (0, 0, 0, 0))
    assert untouched is canvas and scale == 1.0
