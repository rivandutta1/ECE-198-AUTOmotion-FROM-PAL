from src.form_rules import FormMonitor, GOOD, BAD, UNKNOWN
from src.geometry import PoseMeasurement


def sample(tilt=0.0, active=False, valid=True):
    return PoseMeasurement(valid=valid, active=active,
                           torso_angle_deg=tilt if valid else None,
                           reason="TRACKING" if valid else "NO POSE")


def calibrated():
    monitor = FormMonitor()
    monitor.start_calibration()
    for t in range(0, 2100, 100):
        d = monitor.evaluate(sample(0.3), t)
    assert monitor.baseline_deg == 0.3
    assert d.status == UNKNOWN  # arm is still down
    return monitor


def test_uncalibrated_is_unknown():
    assert FormMonitor().evaluate(sample(0, True), 0).status == UNKNOWN


def test_good_then_sustained_bad_then_good():
    m = calibrated()
    assert m.evaluate(sample(0.0, True), 2200).status == GOOD
    for t in range(2300, 3101, 100):
        decision = m.evaluate(sample(22.0, True), t)
    assert decision.status == BAD
    assert m.evaluate(sample(2.0, True), 3200).status == GOOD


def test_short_lean_does_not_warn():
    m = calibrated()
    for t in range(2300, 2700, 100):
        decision = m.evaluate(sample(22.0, True), t)
    assert decision.status == GOOD
    assert m.evaluate(sample(0.0, True), 2800).status == GOOD


def test_lost_pose_and_arm_down_unknown():
    m = calibrated()
    assert m.evaluate(sample(0, False), 2200).status == UNKNOWN
    assert m.evaluate(sample(valid=False), 2300).status == UNKNOWN


def test_moving_during_calibration_rejected():
    m = FormMonitor()
    m.start_calibration()
    for t in range(0, 2100, 100):
        decision = m.evaluate(sample(0.0 if t % 200 == 0 else 12.0), t)
    assert m.baseline_deg is None
    assert decision.status == UNKNOWN
