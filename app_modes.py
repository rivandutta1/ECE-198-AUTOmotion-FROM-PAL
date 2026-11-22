"""The exercises and arms AutoMotion supports, and how to monitor them."""
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


def evaluate_monitor(monitor: ArmExerciseMonitor, landmarks, width, height, ms):
    """Measure the monitor's arm in one frame of landmarks and update the monitor."""
    return monitor.evaluate(measure_arm(landmarks, width, height, side=monitor.side), ms)
