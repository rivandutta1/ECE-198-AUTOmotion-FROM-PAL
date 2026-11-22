"""Only curl/pushdown appear in the production app, legacy modules remain isolated."""
from types import SimpleNamespace

import numpy as np
import pytest

from arm_exercises import Feedback
from app_modes import EXERCISES, SIDES, create_monitor
from arm_ui import WIDTH, HEIGHT, controls, draw_screen, hit_test, point_in_preview
from serial_link import feedback_packet, find_arduino_port
import serial_link as serial_link


def test_only_two_arm_exercise_modes():
    assert EXERCISES == ("curl", "pushdown")
    for exercise in EXERCISES:
        for side in SIDES:
            monitor = create_monitor(exercise, side)
            monitor.start_calibration()
            monitor.reset_reps()
    with pytest.raises(ValueError):
        create_monitor("shoulder", "right")
    with pytest.raises(ValueError):
        create_monitor("chest", "right")


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
    feedback = Feedback("UNKNOWN", "PRESS C TO CALIBRATE", "CAL", 0, 0, "READY")
    for mode in EXERCISES:
        for mirrored in (True, False):
            canvas = draw_screen(frame, None, "right", mode, feedback,
                                 False, mirrored=mirrored, fps=18.3)
            assert canvas.shape == (HEIGHT, WIDTH, 3)
            assert canvas.dtype == np.uint8


def test_serial_packets_for_both_exercises():
    assert feedback_packet("curl", "GOOD", "OK", 3) == b"F,CURL,GOOD,OK,3\n"
    assert feedback_packet("pushdown", "BAD", "LEAN", 2) == b"F,PUSHDOWN,BAD,LEAN,2\n"


def test_autodetect_only_unambiguous_arduino(monkeypatch):
    def fake(device, desc, vid):
        return SimpleNamespace(device=device, description=desc, manufacturer="", vid=vid)
    class Ports:
        @staticmethod
        def comports():
            return [fake("/dev/cu.x", "Arduino Uno R4", 0x2341),
                    fake("/dev/cu.bluetooth", "Bluetooth", None)]
    monkeypatch.setattr(serial_link, "list_ports", Ports)
    assert find_arduino_port() == "/dev/cu.x"
    Ports.comports = lambda: [fake("/dev/cu.x", "Arduino", 0x2341),
                              fake("/dev/cu.y", "Arduino", 0x2341)]
    assert find_arduino_port() is None
