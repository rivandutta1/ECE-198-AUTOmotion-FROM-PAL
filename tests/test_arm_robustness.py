"""Specific regressions for rep completion timing and last-frame errors."""
from arm_exercises import ArmExerciseMonitor
from test_arm_exercises import calibrated, measurement


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
    from arm_exercises import ArmPose
    m = calibrated("pushdown")
    f = m.evaluate(ArmPose(False,"MISSING ARM"), 2400)
    assert f.status == "UNKNOWN"
