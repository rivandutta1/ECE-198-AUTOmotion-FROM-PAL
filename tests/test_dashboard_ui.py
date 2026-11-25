"""arm_ui.py: the dashboard renders for every state, and buttons are clickable."""
from types import SimpleNamespace

import numpy as np

import arm_ui as ui
from app_modes import EXERCISES
from arm_exercises import Feedback
from arm_ui import WIDTH, HEIGHT, controls, draw_screen, hit_test, point_in_preview


def test_large_mouse_targets_and_no_press_buttons():
    unique = set()
    for b in controls():
        x1, y1, x2, y2 = b.rect
        assert x2-x1 >= 175
        assert y2-y1 >= 60
        assert hit_test((x1+x2)//2, (y1+y2)//2) == b.action
        unique.add(b.action)
    assert {"mode:curl", "mode:pushdown", "side:left", "side:right", "mirror",
            "calibrate", "arduino", "camera", "reset", "quit"} <= unique
    assert "mode:shoulder" not in unique and "mode:chest" not in unique
    assert hit_test(1050, 100) is None


def test_mirrored_landmarks_follow_preview():
    p = SimpleNamespace(x=.2, y=.5)
    viewport = (50, 100, 1000, 500)
    assert point_in_preview(p, viewport, False) == (250, 350)
    assert point_in_preview(p, viewport, True) == (850, 350)


def test_render_modes_and_mirror():
    frame = np.full((720, 1280, 3), 100, dtype=np.uint8)
    feedback = Feedback("UNKNOWN", "HOLD STILL 1.2S", "CAL", 0, 0, "READY")
    for mode in EXERCISES:
        for mirrored in (True, False):
            canvas = draw_screen(frame, None, "right", mode, feedback,
                                 False, mirrored=mirrored)
            assert canvas.shape == (HEIGHT, WIDTH, 3)
            assert canvas.dtype == np.uint8


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


def test_dashboard_shows_every_feedback_detail(monkeypatch):
    labels = []
    original = ui._text
    def spy(image, value, *args, **kwargs):
        labels.append(str(value))
        return original(image, value, *args, **kwargs)
    monkeypatch.setattr(ui, "_text", spy)
    frame = np.zeros((720, 1280, 3), np.uint8)
    msg = Feedback("GOOD", "Keep moving steadily", "OK", 3, 1, "CURLING",
                   85, 5, 2, .5, .9, True)
    canvas = ui.draw_screen(frame, None, "right", "curl", msg, True)
    assert canvas.shape == (ui.HEIGHT, ui.WIDTH, 3)
    texts = " | ".join(labels).upper()
    assert "GOOD FORM" in texts and "COMPLETED REPS" in texts
    for label in ("FLAGGED REPS", "STAGE", "CONFIDENCE", "ELBOW ANGLE",
                  "TORSO SHIFT", "UPPER-ARM SHIFT", "REP PROGRESS"):
        assert label in texts
    for value in ("CURLING", "90%", "85\u00b0", "5\u00b0", "2\u00b0", "50%"):
        assert value in texts
    assert "FPS" not in texts
    assert "SHOULDER PRESS" not in texts and "CHEST PRESS" not in texts


def test_missing_measurements_show_a_dash():
    rows = dict((label, value) for label, value, _ in
                ui.detail_rows(Feedback("UNKNOWN", "Show your arm", "TRACK", 0, 0, "READY")))
    assert rows["Elbow angle"] == rows["Confidence"] == rows["Torso shift"] == "-"
    assert rows["Stage"] == "Ready" and rows["Completed reps"] == "0"


def test_details_fit_between_progress_bar_and_calibrate_button():
    calibrate = next(b for b in controls() if b.action == "calibrate")
    assert ui.DETAILS_RECT[3] < calibrate.rect[1]
    assert calibrate.rect[3] < ui.STATUS_RECT[3]


def test_unknown_does_not_appear_as_good():
    frame = np.zeros((360, 640, 3), np.uint8)
    msg = Feedback("UNKNOWN", "Show your arm", "TRACK", 0, 0, "READY")
    assert ui.status_text(msg) == "Move into view"
    assert ui.draw_screen(frame, None, "right", "pushdown", msg, False).shape == (900,1600,3)


def test_font_is_an_installed_family_or_the_qt_default():
    from PySide6.QtGui import QFontDatabase
    family = ui.font_family()
    assert family in QFontDatabase.families() or family == ui.QApplication.font().family()


def test_history_page_renders_with_and_without_entries():
    import history
    sets = [history.CameraSet("2026-11-24 14:03", "Bicep curl", "right", 12, 2)] * 20
    presses = [history.PressSession("2026-11-24 14:05", "Chest press", 5, 32, "1")]
    for args in ((sets, presses), ([], [])):
        image = ui.draw_history(*args)
        assert image.shape == (HEIGHT, WIDTH, 3) and image.sum() > 0


def test_history_button_and_back_button():
    history_button = next(b for b in controls() if b.action == "history")
    x1, y1, x2, y2 = history_button.rect
    assert hit_test((x1 + x2) // 2, (y1 + y2) // 2) == "history"
    back = ui.history_controls()[0]
    x1, y1, x2, y2 = back.rect
    assert hit_test((x1 + x2) // 2, (y1 + y2) // 2, "history") == "back"
    # Live buttons don't respond on the History page.
    assert hit_test(*controls()[0].rect[:2], "history") is None
