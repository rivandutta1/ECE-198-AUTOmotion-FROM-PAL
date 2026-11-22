"""measure_arm(): turning landmarks into joint angles, and rejecting unusable poses."""
from arm_exercises import measure_arm
from landmark_helpers import P, points, measurement


def test_measure_right_and_geometry():
    x = measurement(90)
    assert x.valid
    assert abs(x.elbow_deg - 90) < 1e-6
    assert abs(x.torso_deg) < 1e-6
    assert abs(x.upper_arm_deg) < 1e-6


def test_small_arms_move_back():
    p=points()
    p[14]=P(.5,.31)
    x=measure_arm(p,640,480)
    assert not x.valid


def test_empty_pose_not_good():
    assert not measure_arm(None, 640, 480).valid


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
