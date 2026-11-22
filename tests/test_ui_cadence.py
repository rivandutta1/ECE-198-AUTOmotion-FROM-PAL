"""UI refresh is isolated from camera/inference; test helpers without webcam."""
from types import SimpleNamespace

import numpy as np
import pytest

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
