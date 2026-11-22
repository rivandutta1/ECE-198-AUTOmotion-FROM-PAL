"""Dark minimal layout regression tests (keeps prior test filename compatible)."""
import numpy as np
from arm_exercises import Feedback
import arm_ui as ui


def test_two_modes_two_arms_and_actions_clickable():
    actions = {b.action for b in ui.controls()}
    expected = {"mode:curl", "mode:pushdown", "side:left", "side:right",
                "calibrate", "reset", "mirror", "camera", "arduino", "quit"}
    assert expected <= actions
    assert "mode:chest" not in actions and "mode:shoulder" not in actions
    for b in ui.controls():
        x1, y1, x2, y2 = b.rect
        assert x2-x1 >= 175 and y2-y1 >= 60
        assert ui.hit_test((x1+x2)//2, (y1+y2)//2) == b.action


def test_no_debug_metrics_on_dark_ui(monkeypatch):
    labels = []
    original = ui._text
    def spy(image, value, *args, **kwargs):
        labels.append(str(value))
        return original(image, value, *args, **kwargs)
    monkeypatch.setattr(ui, "_text", spy)
    frame = np.zeros((720, 1280, 3), np.uint8)
    msg = Feedback("GOOD", "Keep moving steadily", "OK", 3, 0, "CURLING",
                   85, 5, 2, .5, .9, True)
    canvas = ui.draw_screen(frame, None, "right", "curl", msg, True)
    assert canvas.shape == (ui.HEIGHT, ui.WIDTH, 3)
    texts = " | ".join(labels).upper()
    assert "GOOD FORM" in texts and "COMPLETED REPS" in texts
    assert "ELBOW ANGLE" not in texts and "TORSO SHIFT" not in texts
    assert "FPS" not in texts and "STAGE:" not in texts
    assert "SHOULDER PRESS" not in texts and "CHEST PRESS" not in texts


def test_unknown_does_not_appear_as_good():
    frame = np.zeros((360, 640, 3), np.uint8)
    msg = Feedback("UNKNOWN", "Show your arm", "TRACK", 0, 0, "READY")
    assert ui.status_text(msg) == "Move into view"
    assert ui.draw_screen(frame, None, "right", "pushdown", msg, False).shape == (900,1600,3)
