"""Exercise switching and frame delivery stay off the UI thread."""
import sys
import threading
import time
import types

import numpy as np
import pytest

import main


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
