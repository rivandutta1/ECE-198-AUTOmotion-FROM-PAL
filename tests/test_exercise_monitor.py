"""ArmExerciseMonitor: calibration, form warnings, rep counting and tracking loss.

Uses synthetic landmarks: not a test of physical accuracy or clinical validity.
"""
import pytest

from arm_exercises import ArmExerciseMonitor, ArmPose, measure_arm, GOOD, BAD, UNKNOWN
from landmark_helpers import points, measurement, calibrated, feed


def test_no_calibration_unknown():
    m = ArmExerciseMonitor()
    x = m.evaluate(measurement(165), 100)
    assert x.status == UNKNOWN and x.issue == "CAL"


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


def test_fast_fake_rep_rejected():
    m = calibrated("curl")
    m.phase = "LOWERING"
    m.needs_home = False
    m.rep_start_ms = 2400
    m._complete(2550)
    assert m.reps == 0
    assert m.last_issue == "ROM"


def test_repeated_threshold_bounce_does_not_double_count():
    m = calibrated("curl")
    m.phase = "LOWERING"
    m.needs_home = False
    m.rep_start_ms = 2100
    m._complete(2700)
    assert m.reps == 1
    m.phase = "LOWERING"
    m.rep_start_ms = 2720
    m._complete(2800)
    assert m.reps == 1


def test_last_frame_lean_warning_is_attributed_to_finished_rep():
    m = calibrated("curl")
    m.warning_hold_ms = 0
    m.needs_home = False
    m.phase = "LOWERING"
    m.rep_start_ms = 2300
    m.angles = [165, 165, 165]
    m.torso_angles = [20.0, 20.0, 20.0]
    m.upper_angles = [0.0, 0.0, 0.0]
    result = m.evaluate(measurement(165, shoulder_x=.61), 3000)
    assert result.reps == 1
    assert result.bad_reps == 1
    assert result.status == "BAD"


def test_missing_pose_does_not_report_good():
    m = calibrated("pushdown")
    f = m.evaluate(ArmPose(False,"MISSING ARM"), 2400)
    assert f.status == "UNKNOWN"


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
