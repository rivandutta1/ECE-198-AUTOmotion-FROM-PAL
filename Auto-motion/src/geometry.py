"""Turn normalized pose landmarks into a single side-view torso measurement.

This is an experimental large-torso-lean detector, NOT a clinical form assessment.
"""
from dataclasses import dataclass
from math import atan2, degrees, hypot
from typing import Any, Optional, Sequence
from src.data_types import PoseFrame 

@dataclass(frozen=True)
class PoseMeasurement:
    valid: bool
    active: bool
    torso_angle_deg: Optional[float]
    reason: str


SIDE_INDEX = {
    "left": (11, 13, 15, 23),   # shoulder, elbow, wrist, hip
    "right": (12, 14, 16, 24),
}


def _quality(landmark: Any, threshold: float) -> bool:
    if not (0.02 <= landmark.x <= 0.98 and 0.02 <= landmark.y <= 0.98):
        return False
    for key in ("visibility", "presence"):
        value = getattr(landmark, key, None)
        if value is not None and value < threshold:
            return False
    return True


def measure_pose(
    landmarks: Optional[Sequence[Any]], width: int, height: int,
    side: str = "left", visibility_threshold: float = 0.6,
) -> PoseMeasurement:
    """Use pixel-scaled positions: degrees of hip->shoulder from image vertical.

    The selected arm must have its wrist above the shoulder to be 'active'.
    Missing/occluded/out-of-frame data becomes UNKNOWN, not GOOD or BAD.
    """
    if side not in SIDE_INDEX:
        raise ValueError("side must be 'left' or 'right'")
    if not landmarks or len(landmarks) < 33 or width < 1 or height < 1:
        return PoseMeasurement(False, False, None, "NO POSE")
    shoulder_i, elbow_i, wrist_i, hip_i = SIDE_INDEX[side]
    shoulder, elbow, wrist, hip = (
        landmarks[shoulder_i], landmarks[elbow_i],
        landmarks[wrist_i], landmarks[hip_i]
    )
    if not all(_quality(j, visibility_threshold) for j in (shoulder, elbow, wrist, hip)):
        return PoseMeasurement(False, False, None, "JOINT HIDDEN / OUT OF FRAME")

    dx = (shoulder.x - hip.x) * width
    up = (hip.y - shoulder.y) * height
    if up < 25 or hypot(dx, up) < 60:
        return PoseMeasurement(False, False, None, "MOVE BACK: SHOW TORSO")

    # 0 deg means vertical hip->shoulder; positive/negative denotes lean.
    tilt = degrees(atan2(dx, up))
    active = wrist.y < shoulder.y - 0.025
    return PoseMeasurement(True, active, tilt, "ARM NOT OVERHEAD" if not active else "TRACKING")


def measure_pose_frame(
    pose: PoseFrame,
    width: int,
    height: int,
    side: str = "left",
) -> PoseMeasurement:
    """Measure torso lean using AUTO-MOTION's pixel-coordinate PoseFrame."""

    if side not in ("left", "right"):
        raise ValueError("side must be 'left' or 'right'")

    if not pose.valid or width < 1 or height < 1:
        return PoseMeasurement(False, False, None, "NO VALID POSE")

    names = ("shoulder", "elbow", "wrist", "hip")
    joints = [
        pose.landmarks.get(f"{side}_{name}")
        for name in names
    ]

    if any(joint is None for joint in joints):
        return PoseMeasurement(
            False, False, None, "JOINT HIDDEN / OUT OF FRAME"
        )

    shoulder, elbow, wrist, hip = joints

    for joint in joints:
        if joint.visibility < 0.6:
            return PoseMeasurement(
                False, False, None, "JOINT NOT VISIBLE"
            )

        if not (
            0.02 * width <= joint.x <= 0.98 * width
            and 0.02 * height <= joint.y <= 0.98 * height
        ):
            return PoseMeasurement(
                False, False, None, "JOINT OUT OF FRAME"
            )

    dx = shoulder.x - hip.x
    up = hip.y - shoulder.y

    if up < 25 or hypot(dx, up) < 60:
        return PoseMeasurement(
            False, False, None, "MOVE BACK: SHOW TORSO"
        )

    tilt = degrees(atan2(dx, up))
    active = wrist.y < shoulder.y - (0.025 * height)

    return PoseMeasurement(
        valid=True,
        active=active,
        torso_angle_deg=tilt,
        reason="TRACKING" if active else "ARM NOT OVERHEAD"
    )
