from dataclasses import dataclass
from src.geometry import measure_pose

@dataclass
class P:
    x: float = 0.5
    y: float = 0.5
    visibility: float = 0.99
    presence: float = 0.99


def make_points(wrist_up=True):
    points = [P() for _ in range(33)]
    points[11] = P(0.5, 0.4)  # shoulder
    points[13] = P(0.5, 0.35) # elbow
    points[15] = P(0.5, 0.22 if wrist_up else 0.5)
    points[23] = P(0.5, 0.75) # hip
    return points


def test_upright():
    m = measure_pose(make_points(), 640, 480)
    assert m.valid and m.active
    assert abs(m.torso_angle_deg) < 0.01


def test_arm_down():
    m = measure_pose(make_points(False), 640, 480)
    assert m.valid and not m.active


def test_hidden_wrist():
    ps = make_points()
    ps[15].visibility = 0.1
    assert not measure_pose(ps, 640, 480).valid


def test_torso_tilt():
    ps = make_points()
    ps[11].x = 0.6
    m = measure_pose(ps, 640, 480)
    assert m.valid and m.torso_angle_deg > 10
