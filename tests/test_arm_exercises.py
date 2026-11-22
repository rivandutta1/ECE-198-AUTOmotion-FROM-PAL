"""Synthetic landmark tests: not physical accuracy or clinical validation."""
from dataclasses import dataclass
from math import sin, cos, radians

import pytest

from arm_exercises import ArmExerciseMonitor, measure_arm, GOOD, BAD, UNKNOWN


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


def test_no_calibration_unknown():
    m = ArmExerciseMonitor()
    x = m.evaluate(measurement(165), 100)
    assert x.status == UNKNOWN and x.issue == "CAL"


def test_measure_right_and_geometry():
    x = measurement(90)
    assert x.valid
    assert abs(x.elbow_deg - 90) < 1e-6
    assert abs(x.torso_deg) < 1e-6
    assert abs(x.upper_arm_deg) < 1e-6


def test_missing_arm_returns_unknown_and_instructions():
    p = measure_arm(points(165, wrist_visible=False), 640, 480)
    assert not p.valid and "RIGHT WRIST" in p.reason
    m = calibrated()
    f = m.evaluate(p, 2200)
    assert f.status == UNKNOWN and f.issue == "TRACK"


def test_curl_good_rep():
    m = calibrated("curl")
    values = [165,145,125,110,95,85,95,115,140,155,165,165]
    rs = feed(m, values)
    assert any(x.status == GOOD for x in rs)
    assert rs[-1].reps == 1
    assert rs[-1].bad_reps == 0


def test_curl_partial_rom_is_bad_not_a_rep():
    m = calibrated("curl")
    rs = feed(m, [165,140,125,115,125,140,153,165])
    assert rs[-1].status == BAD
    assert rs[-1].issue == "ROM"
    assert m.reps == 0


def test_pushdown_good_rep():
    m = calibrated("pushdown")
    rs = feed(m, [100,110,130,140,155,165,172,160,140,120,110,100])
    assert any(x.status == GOOD for x in rs)
    assert rs[-1].reps == 1


def test_pushdown_partial_is_bad():
    m = calibrated("pushdown")
    rs = feed(m, [100,115,138,145,153,145,128,114,105])
    assert rs[-1].status == BAD and rs[-1].issue == "ROM"
    assert m.reps == 0


def test_torso_lean_sustained_warning():
    m = calibrated("curl")
    # Need to start movement first; lean shifts shoulder and elbow together.
    feed(m, [165,125,110], 2100, 120)
    outcomes=[]
    for t in range(2600, 3250, 100):
        outcomes.append(m.evaluate(measurement(110, shoulder_x=.61), t))
    assert outcomes[-1].status == BAD
    assert outcomes[-1].issue == "LEAN"


def test_short_lean_not_bad():
    m = calibrated("curl")
    outcomes=[m.evaluate(measurement(115, shoulder_x=.61), t) for t in [2200,2300,2350]]
    assert all(x.status != BAD for x in outcomes)


def test_upper_arm_drift_warning():
    m = calibrated("curl")
    outcomes=[m.evaluate(measurement(110, elbow_x=.59), t) for t in range(2200,2950,100)]
    assert outcomes[-1].status == BAD
    assert outcomes[-1].issue == "ARM"


def test_prolonged_tracking_loss_requires_start_position():
    m=calibrated("curl")
    feed(m,[165,125,90],2100)
    lost = measure_arm(None, 640, 480)
    assert m.evaluate(lost,2600).status == UNKNOWN
    assert m.evaluate(lost,3250).status == UNKNOWN
    x=m.evaluate(measurement(90),3350)
    assert x.status == UNKNOWN and x.issue == "START"
    feed(m,[165,165],3500)
    assert m.reps == 0


def test_single_bad_frame_does_not_reset_rep_sequence():
    m=calibrated("curl")
    feed(m,[165,125,90,90],2100)
    assert m.phase == "LOWERING"
    invalid=measure_arm(None,640,480)
    assert m.evaluate(invalid,2600).status==UNKNOWN
    # Return during a short dropout: the motion continues instead of resetting.
    f=m.evaluate(measurement(155),2700)
    assert f.status in (GOOD, UNKNOWN)
    f=m.evaluate(measurement(165),2800)
    assert f.status in (GOOD, UNKNOWN)
    assert m.reps==1


def test_reset_reps_keeps_calibration():
    m=calibrated("curl")
    feed(m,[165,130,95,85,115,155,165],2100)
    assert m.reps==1
    m.reset_reps()
    assert m.reps==0 and m.calibrated


def test_calibration_rejects_moving_arm():
    m=ArmExerciseMonitor("curl")
    m.start_calibration()
    for t in range(0,1801,100):
        f=m.evaluate(measurement(165 if t%200==0 else 148),t)
    assert not m.calibrated
    assert f.status==UNKNOWN and "MOVED" in f.message


def test_calibration_requires_correct_start_pose():
    m=ArmExerciseMonitor("pushdown")
    m.start_calibration()
    assert "BEND ELBOW" in m.evaluate(measurement(165),0).message


def test_wrong_mode_and_side_rejected():
    with pytest.raises(ValueError): ArmExerciseMonitor("bench")
    with pytest.raises(ValueError): measure_arm(points(),640,480,side="middle")


def test_small_arms_move_back():
    p=points()
    p[14]=P(.5,.31)
    x=measure_arm(p,640,480)
    assert not x.valid


def test_empty_pose_not_good():
    assert not measure_arm(None, 640, 480).valid
