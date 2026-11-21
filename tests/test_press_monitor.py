"""Synthetic geometry tests; NOT physical seated chest-press validation."""
from dataclasses import dataclass

from src.press_monitor import PressMonitor, GOOD, BAD, UNKNOWN, angular_change, joint_angle
from src.serial_link import feedback_packet


@dataclass
class P:
    x: float = 0.5
    y: float = 0.5
    visibility: float = 0.99
    presence: float = 0.99


def points(exercise="shoulder", bent=False):
    ps = [P() for _ in range(33)]
    for sh, el, wr, idx, hip in ((11, 13, 15, 19, 23), (12, 14, 16, 20, 24)):
        if exercise == "shoulder":
            ps[sh] = P(0.50, 0.40)
            ps[el] = P(0.50, 0.34)
            ps[wr] = P(0.50, 0.56 if bent else 0.21)
            ps[idx] = P(0.50, 0.61 if bent else 0.13)
            ps[hip] = P(0.50, 0.76)
        else:
            # Upright SEATED chest press: hips below shoulders; hands
            # move forward from chest toward arm extension, not overhead.
            ps[sh] = P(0.40, 0.40)
            ps[el] = P(0.52, 0.44) if bent else P(0.64, 0.42)
            ps[wr] = P(0.49, 0.53) if bent else P(0.85, 0.44)
            ps[idx] = P(0.46, 0.60) if bent else P(0.93, 0.45)
            ps[hip] = P(0.40, 0.74)
    return ps


def calibrated_shoulder():
    m = PressMonitor("shoulder")
    m.start_calibration()
    for t in range(0, 2100, 100):
        m.evaluate(points("shoulder", bent=True), 640, 480, t)
    assert m.baseline_deg is not None
    return m


def calibrated_chest():
    m = PressMonitor("chest")
    m.start_calibration()
    for t in range(0, 2100, 100):
        m.evaluate(points("chest", bent=True), 640, 480, t)
    assert m.baseline_deg is not None
    return m


def test_shoulder_starts_unknown_and_upright_is_good():
    m = PressMonitor("shoulder")
    assert m.evaluate(points(), 640, 480, 0).status == UNKNOWN
    m = calibrated_shoulder()
    assert m.evaluate(points(), 640, 480, 2300).status == GOOD


def test_shoulder_sustained_lean_uses_existing_form_monitor_timer():
    m = calibrated_shoulder()
    leaning = points()
    leaning[11].x = 0.65
    for t in range(2200, 3001, 100):
        result = m.evaluate(leaning, 640, 480, t)
    assert result.status == BAD
    assert result.issue == "LEAN"
    assert m.evaluate(points(), 640, 480, 3100).status == GOOD


def test_missing_landmarks_unknown():
    m = calibrated_shoulder()
    assert m.evaluate(None, 640, 480, 2200).status == UNKNOWN
    m = calibrated_chest()
    assert m.evaluate(None, 640, 480, 2200).status == UNKNOWN


def test_chest_not_active_without_movement_then_evaluates():
    m = calibrated_chest()
    assert m.evaluate(points("chest", bent=True), 640, 480, 2200).status == UNKNOWN
    result = m.evaluate(points("chest"), 640, 480, 2300)
    assert result.status == GOOD
    assert result.checks["rom"] == "PASS"


def test_chest_bottom_to_top_counts_projected_rom():
    m = calibrated_chest()
    m.evaluate(points("chest", bent=True), 640, 480, 2200)
    result = m.evaluate(points("chest"), 640, 480, 2300)
    assert result.checks["rom"] == "PASS"


def test_invalid_packets_rejected():
    assert feedback_packet("CHEST", "BAD", "ARM", 0) == b"F,CHEST,BAD,ARM,0\n"
    assert feedback_packet("SHOULDER", "UNKNOWN", "CAL", 0) == b"F,SHOULDER,UNKNOWN,CAL,0\n"
    try:
        feedback_packet("CHEST", "GOOD", "USER_STRING\nBAD", 0)
        assert False, "invalid reason should be rejected"
    except ValueError:
        pass


def test_angle_wrap():
    assert angular_change(179, -179) == 2
    assert round(joint_angle(P(0.5,0.0), P(0.5,0.5), P(0.5,1.0), 640,480)) == 180


def test_shoulder_symmetry_warning_only_after_hold():
    m = calibrated_shoulder()
    differing = points("shoulder")
    # Left arm extended; right arm substantially bent.
    differing[16] = P(0.70, 0.34)
    first = m.evaluate(differing, 640, 480, 2200)
    assert first.status == GOOD
    for t in range(2300, 3001, 100):
        last = m.evaluate(differing, 640, 480, t)
    assert last.status == BAD
    assert last.issue == "ASYMMETRY"
    assert m.evaluate(points("shoulder"), 640, 480, 3100).status == GOOD


def test_chest_rejects_unstable_calibration():
    m = PressMonitor("chest")
    m.start_calibration()
    for t in range(0, 2100, 100):
        ps = points("chest", bent=True)
        if t % 200 == 0:
            ps[11].x -= 0.15
        outcome = m.evaluate(ps, 640, 480, t)
    assert m.baseline_deg is None
    assert outcome.status == UNKNOWN
    assert outcome.issue == "CAL"


def test_chest_calibration_rejects_lying_pose():
    m = PressMonitor("chest")
    m.start_calibration()
    ps = points("chest", bent=True)
    # Set hip far sideways instead of below shoulder (near horizontal).
    ps[23] = P(0.82, 0.40)
    result = m.evaluate(ps, 640, 480, 0)
    assert result.status == UNKNOWN
    assert "SIT UPRIGHT" in result.detail
    assert m.baseline_deg is None


def test_chest_seated_calibration_baseline_near_vertical():
    m = calibrated_chest()
    assert abs(m.baseline_deg) < 5
