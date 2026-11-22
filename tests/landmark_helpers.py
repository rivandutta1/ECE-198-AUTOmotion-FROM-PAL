"""Synthetic MediaPipe-style landmarks shared by the arm tests (not a test file)."""
from dataclasses import dataclass
from math import sin, cos, radians

from arm_exercises import ArmExerciseMonitor, measure_arm, UNKNOWN


@dataclass
class P:
    x: float = .5
    y: float = .5
    visibility: float = .99
    presence: float = .99


def points(angle=165, shoulder_x=.50, elbow_x=None, wrist_visible=True, right=True,
           wrist_x_shift=0.0):
    """A synthetic arm joint with elbow angle 'angle' in image pixel space."""
    out = [P() for _ in range(33)]
    sw = 12 if right else 11
    ew = 14 if right else 13
    ww = 16 if right else 15
    hw = 24 if right else 23
    shoulder = P(shoulder_x, .30)
    elbow = P(shoulder_x if elbow_x is None else elbow_x, .48)
    # Build wrist from measured elbow->shoulder direction (for arm drift tests too).
    ax = (shoulder.x-elbow.x)*640
    ay = (shoulder.y-elbow.y)*480
    from math import hypot, atan2
    base = atan2(ay, ax)
    direction = base + radians(angle)
    wrist = P(elbow.x + (76*cos(direction))/640 + wrist_x_shift,
              elbow.y + (76*sin(direction))/480)
    if not wrist_visible:
        wrist.visibility = .10
    out[sw], out[ew], out[ww], out[hw] = shoulder, elbow, wrist, P(.5, .76)
    return out


def measurement(angle, **kwargs):
    return measure_arm(points(angle, **kwargs), 640, 480)


def calibrated(exercise="curl"):
    m = ArmExerciseMonitor(exercise=exercise)
    m.start_calibration()
    start_angle = 165 if exercise == "curl" else 100
    for t in range(0, 1801, 100):
        last = m.evaluate(measurement(start_angle), t)
    assert m.calibrated, last
    assert m.evaluate(measurement(start_angle), 1900).status == UNKNOWN
    assert m.evaluate(measurement(start_angle), 2000).status == UNKNOWN
    return m


def feed(m, angles, start=2100, step=130):
    return [m.evaluate(measurement(angle), start+i*step) for i,angle in enumerate(angles)]
