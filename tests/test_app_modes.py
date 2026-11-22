"""app_modes.py: only curl and pushdown, on either arm, can be monitored."""
import pytest

from app_modes import EXERCISES, SIDES, create_monitor


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
