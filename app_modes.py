"""The two exercise modes supported by AutoMotion's current public interface.

The legacy press monitor remains as an unused file so shared branches are not
silently deleted; it is not imported or reachable through the UI/CLI.
"""
from arm_exercises import ArmExerciseMonitor, measure_arm

EXERCISES = ("curl", "pushdown")
SIDES = ("right", "left")
EXERCISE_NAMES = {"curl": "Bicep curl", "pushdown": "Tricep pushdown"}


def create_monitor(exercise: str, side: str):
    if exercise not in EXERCISES:
        raise ValueError(f"Exercise not supported: {exercise}")
    if side not in SIDES:
        raise ValueError(f"Side not supported: {side}")
    return ArmExerciseMonitor(exercise, side=side)


def evaluate_monitor(monitor, exercise, side, landmarks, width, height, ms):
    if exercise not in EXERCISES:
        raise ValueError(f"Exercise not supported: {exercise}")
    return monitor.evaluate(measure_arm(landmarks, width, height, side=side), ms)
