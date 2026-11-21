import numpy as np
from src.arm_exercises import Feedback
from src.arm_ui import draw_screen


def test_live_dashboard_shapes_and_unknown():
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    feedback = Feedback("UNKNOWN", "SHOW RIGHT WRIST IN FRAME", "TRACK", 0, 0, "READY")
    result = draw_screen(frame, None, "right", "curl", feedback, False)
    assert result.shape == (900, 1600, 3)
    assert result.dtype == np.uint8
    assert result.sum() > 0


def test_live_dashboard_good_and_bad():
    frame = np.zeros((360, 640, 3), dtype=np.uint8)
    for status, issue in (("GOOD", "OK"),("BAD", "LEAN")):
        feedback = Feedback(status, "TEST MESSAGE", issue, 4, 1, "CURLING", 98., 2., 5., .7, .95, True)
        assert draw_screen(frame, None, "right", "curl", feedback, True).shape == (900,1600,3)
