"""Confidence and dropout regression tests. No camera or Arduino required."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from test_arm_exercises import points, measurement, calibrated
from arm_exercises import ArmExerciseMonitor, measure_arm, UNKNOWN


def test_confidence_just_above_new_gate_is_accepted():
    joints = points(165)
    for i in (12, 14, 16, 24):
        joints[i].visibility = 0.50
        joints[i].presence = 0.40
    pose = measure_arm(joints, 640, 480)
    assert pose.valid and 0.39 <= pose.confidence <= 0.41


def test_low_visibility_still_returns_unknown():
    joints = points(165)
    joints[16].visibility = 0.10
    pose = measure_arm(joints, 640, 480)
    assert not pose.valid and "WRIST" in pose.reason


def test_unset_presence_and_visibility_do_not_crash():
    joints = points(165)
    joints[16].visibility = None
    joints[16].presence = None
    assert measure_arm(joints, 640, 480).valid


def test_other_hip_fallback_if_selected_hip_hidden():
    joints = points(165)
    joints[24].visibility = 0.10
    joints[23].x, joints[23].y = 0.51, 0.76
    assert measure_arm(joints, 640, 480).valid


def test_both_hips_hidden_remains_unknown():
    joints = points(165)
    joints[24].visibility = joints[23].visibility = 0.10
    pose = measure_arm(joints, 640, 480)
    assert not pose.valid and "HIPS" in pose.reason


def test_very_near_edge_allowed_but_offscreen_rejected():
    joints = points(165, shoulder_x=0.08)
    # Track an arm near (but not outside) the left edge of the image.
    joints[24].x = 0.09
    assert measure_arm(joints, 640, 480).valid
    joints[12].x = -0.02
    pose = measure_arm(joints, 640, 480)
    assert not pose.valid and "MOVE BACK" in pose.reason


def test_calibration_short_missing_frame_not_start_over():
    m = ArmExerciseMonitor("curl", calibration_ms=1500)
    m.start_calibration()
    for t in range(0, 901, 100):
        m.evaluate(measurement(165), t)
    n = len(m.samples)
    assert n >= 9
    assert m.evaluate(measure_arm(None, 640, 480), 950).status == UNKNOWN
    assert len(m.samples) == n
    for t in range(1000, 1801, 100):
        outcome = m.evaluate(measurement(165), t)
    assert m.calibrated and outcome.calibrated


def test_calibration_long_missing_period_resets_samples():
    m = ArmExerciseMonitor("curl", calibration_ms=1500)
    m.start_calibration()
    for t in range(0, 901, 100):
        m.evaluate(measurement(165), t)
    m.evaluate(measure_arm(None, 640, 480), 1600)
    x = m.evaluate(measurement(165), 1700)
    assert not m.calibrated
    assert len(m.samples) == 1
    assert x.status == UNKNOWN


def test_unknown_not_false_good_after_occlusion():
    m = calibrated("curl")
    m.evaluate(measurement(165), 2100)
    m.evaluate(measurement(110), 2250)
    for t in (2400, 2510, 2720, 2900):
        f = m.evaluate(measure_arm(None, 640, 480), t)
        assert f.status == UNKNOWN
    assert m.reps == 0
