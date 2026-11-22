"""Right/left side-view curl and cable pushdown feedback, no camera dependency.

Single-camera 2D screening only: measurements and thresholds are approximate,
not an assessment of load, shoulder rotation, grip, pain or exercise safety.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import atan2, degrees, hypot, acos, isfinite
from statistics import median
from typing import Any, Optional, Sequence

GOOD = "GOOD"
BAD = "BAD"
UNKNOWN = "UNKNOWN"

JOINTS = {
    "left": {"shoulder": 11, "elbow": 13, "wrist": 15, "hip": 23},
    "right": {"shoulder": 12, "elbow": 14, "wrist": 16, "hip": 24},
}


def _angle(a, b, c) -> float:
    """Angle at b; coordinates must be in pixels."""
    ax, ay = a[0] - b[0], a[1] - b[1]
    cx, cy = c[0] - b[0], c[1] - b[1]
    length = hypot(ax, ay) * hypot(cx, cy)
    if length < 1e-6:
        raise ValueError("JOINTS TOO CLOSE")
    cos_theta = max(-1.0, min(1.0, (ax * cx + ay * cy) / length))
    return degrees(acos(cos_theta))


@dataclass(frozen=True)
class ArmPose:
    valid: bool
    reason: str
    elbow_deg: Optional[float] = None
    torso_deg: Optional[float] = None
    upper_arm_deg: Optional[float] = None
    confidence: Optional[float] = None


def _quality(point) -> tuple[float, float]:
    """MediaPipe can leave presence/visibility unset; None isn't low confidence."""
    def score(name):
        value = getattr(point, name, None)
        if value is None:
            return 1.0
        try:
            value = float(value)
        except (ValueError, TypeError):
            return 0.0
        return value if isfinite(value) else 0.0
    return score("visibility"), score("presence")


def measure_arm(landmarks: Optional[Sequence[Any]], width: int, height: int,
                side: str = "right", min_visibility: float = 0.45,
                min_presence: float = 0.35) -> ArmPose:
    """Measure 2D joints with adaptive size checks and useful missing-joint prompts.

    Thresholds are intentionally more tolerant than the previous 0.65 gate;
    occluded/off-frame or physically implausible joints still return UNKNOWN.
    """
    if side not in JOINTS:
        raise ValueError("side must be right or left")
    if landmarks is None or len(landmarks) < 33 or width <= 0 or height <= 0:
        return ArmPose(False, f"STEP BACK UNTIL {side.upper()} ARM AND HIP ARE VISIBLE")
    points = {}
    confidence = 1.0

    def get_point(idx):
        lm = landmarks[idx]
        x, y = getattr(lm, "x", None), getattr(lm, "y", None)
        try:
            x, y = float(x), float(y)
        except (TypeError, ValueError):
            return None, "POSITION"
        if not (isfinite(x) and isfinite(y)):
            return None, "POSITION"
        if not (0.005 <= x <= 0.995 and 0.005 <= y <= 0.995):
            return None, "FRAME"
        visible, present = _quality(lm)
        if visible < min_visibility or present < min_presence:
            return None, "VISIBILITY"
        return ((x * width, y * height), min(visible, present)), "OK"

    for joint in ("shoulder", "elbow", "wrist"):
        result, why = get_point(JOINTS[side][joint])
        if result is None:
            if why == "FRAME":
                return ArmPose(False, f"MOVE BACK: {side.upper()} {joint.upper()} OFF SCREEN")
            return ArmPose(False, f"SHOW {side.upper()} {joint.upper()} IN FRAME")
        points[joint], score = result
        confidence = min(confidence, score)

    # The opposite hip can help with a side view where the near arm occludes
    # its hip. We never invent a hip or estimate torso lean from the arm alone.
    hip_result, _ = get_point(JOINTS[side]["hip"])
    if hip_result is None:
        opposite = "left" if side == "right" else "right"
        hip_result, _ = get_point(JOINTS[opposite]["hip"])
    if hip_result is None:
        return ArmPose(False, "SHOW HIPS: STEP BACK OR TURN SLIGHTLY")
    points["hip"], score = hip_result
    confidence = min(confidence, score)

    shoulder, elbow, wrist, hip = (points[name] for name in
                                   ("shoulder", "elbow", "wrist", "hip"))
    # Scale with the frame instead of assuming every camera uses 640x480.
    min_arm = max(12.0, min(width, height) * 0.030)
    if (hypot(shoulder[0]-elbow[0], shoulder[1]-elbow[1]) < min_arm or
            hypot(elbow[0]-wrist[0], elbow[1]-wrist[1]) < min_arm):
        return ArmPose(False, "MOVE BACK OR TURN SIDEWAYS: ARM JOINTS OVERLAP")
    up = hip[1] - shoulder[1]
    min_torso = max(30.0, height * 0.105)
    if up < min_torso or hypot(hip[0]-shoulder[0], hip[1]-shoulder[1]) < min_torso:
        return ArmPose(False, "SHOW HIP BELOW SHOULDER - MOVE CAMERA BACK")
    try:
        elbow_deg = _angle(shoulder, elbow, wrist)
        upper_deg = _angle(elbow, shoulder, hip)
    except ValueError:
        return ArmPose(False, "MOVE BACK: SEPARATE THE ARM JOINTS")
    torso_deg = degrees(atan2(shoulder[0] - hip[0], up))
    return ArmPose(True, "TRACKING", elbow_deg, torso_deg, upper_deg, confidence)


@dataclass(frozen=True)
class Feedback:
    status: str
    message: str
    issue: str
    reps: int
    bad_reps: int
    stage: str
    elbow_deg: Optional[float] = None
    torso_change_deg: Optional[float] = None
    upper_arm_change_deg: Optional[float] = None
    progress: float = 0.0
    confidence: Optional[float] = None
    calibrated: bool = False


class ArmExerciseMonitor:
    """Calibrated, debounced, single-arm exercise monitor with rep state machine.

    Default limits are *experimental prototype values* and must be evaluated
    with controlled real-world trials for every camera position/person.
    """
    def __init__(self, exercise: str = "curl", side: str = "right",
                 calibration_ms: int = 1500, warning_hold_ms: int = 400,
                 min_rep_ms: int = 400, rep_cooldown_ms: int = 300):
        if exercise not in ("curl", "pushdown"):
            raise ValueError("exercise must be curl or pushdown")
        if side not in JOINTS:
            raise ValueError("side must be right or left")
        self.exercise = exercise
        self.side = side
        self.calibration_ms = calibration_ms
        self.warning_hold_ms = warning_hold_ms
        self.min_rep_ms = min_rep_ms
        self.rep_cooldown_ms = rep_cooldown_ms
        self.reset()

    def reset(self) -> None:
        self.calibrating = False
        self.calibration_error = ""
        self.samples: list[tuple[int, ArmPose]] = []
        self.calibrated = False
        self.base_torso = None
        self.base_upper = None
        self.reps = 0
        self.bad_reps = 0
        self.phase = "READY"
        self.needs_home = True
        self.angles: list[float] = []
        self.torso_angles: list[float] = []
        self.upper_angles: list[float] = []
        self.rep_bad = False
        self.bad_since: dict[str, int] = {}
        self.issue_until = -1
        self.last_issue = "OK"
        self.last_message = ""
        self.last_rep_ms = -999999
        self.rep_start_ms: Optional[int] = None
        self.missing_since_ms: Optional[int] = None
        self.last_calibration_valid_ms: Optional[int] = None

    def reset_reps(self) -> None:
        """Reset session counters without erasing a good calibration."""
        self.reps = 0
        self.bad_reps = 0
        self.phase = "READY"
        self.needs_home = True
        self.angles.clear()
        self.torso_angles.clear()
        self.upper_angles.clear()
        self.bad_since.clear()
        self.rep_bad = False
        self.issue_until = -1
        self.last_rep_ms = -999999
        self.rep_start_ms = None

    def start_calibration(self) -> None:
        self.reset()
        self.calibrating = True

    def _feedback(self, status, message, issue, pose=None, progress=0.0,
                  torso_change=None, upper_change=None, elbow=None):
        return Feedback(
            status, message, issue, self.reps, self.bad_reps, self.phase,
            elbow if elbow is not None else (pose.elbow_deg if pose else None),
            torso_change, upper_change, progress,
            pose.confidence if pose else None, self.calibrated,
        )

    def _home(self, angle: float) -> bool:
        return angle >= 150 if self.exercise == "curl" else angle <= 115

    def _progress(self, angle: float) -> float:
        if self.exercise == "curl":
            return max(0.0, min(1.0, (155.0 - angle) / 65.0))
        return max(0.0, min(1.0, (angle - 110.0) / 50.0))

    def _clear_samples_after_gap(self, ms: int) -> None:
        """Restart calibration if there has been no usable frame for 500 ms."""
        if (self.last_calibration_valid_ms is None or
                ms - self.last_calibration_valid_ms > 500):
            self.samples.clear()

    def _calibration(self, pose: ArmPose, ms: int) -> Feedback:
        if not pose.valid:
            # One bad inference frame should not restart 1.5s of calibration.
            self._clear_samples_after_gap(ms)
            return self._feedback(UNKNOWN, pose.reason, "TRACK", pose)
        # Record rest posture only. It determines a personal torso / upper-arm baseline.
        if self.exercise == "curl" and pose.elbow_deg < 145:
            self._clear_samples_after_gap(ms)
            return self._feedback(UNKNOWN, "RELAX ARM STRAIGHT DOWN TO CALIBRATE", "START", pose)
        if self.exercise == "pushdown" and not (65 <= pose.elbow_deg <= 135):
            self._clear_samples_after_gap(ms)
            return self._feedback(UNKNOWN, "BEND ELBOW AT START OF PUSHDOWN", "START", pose)
        if (self.last_calibration_valid_ms is not None and
                ms - self.last_calibration_valid_ms > 500):
            self.samples.clear()
        self.last_calibration_valid_ms = ms
        self.samples.append((ms, pose))
        elapsed = ms - self.samples[0][0]
        if elapsed < self.calibration_ms or len(self.samples) < 10:
            return self._feedback(UNKNOWN, f"HOLD STILL {max(0, self.calibration_ms - elapsed) / 1000:.1f}S", "CAL", pose)
        torsos = [s.torso_deg for _, s in self.samples]
        uppers = [s.upper_arm_deg for _, s in self.samples]
        elbows = [s.elbow_deg for _, s in self.samples]
        self.samples = []
        self.calibrating = False
        # Ignore the most extreme 10% on each side when measuring stability;
        # a single noisy landmark shouldn't invalidate the calibration.
        def robust_span(values):
            ordered = sorted(values)
            cut = max(1, int(len(ordered) * 0.10))
            return ordered[-cut-1] - ordered[cut]
        if (robust_span(torsos) > 7 or
                robust_span(uppers) > 11 or
                robust_span(elbows) > 14):
            self.calibration_error = "YOU MOVED: PRESS C TO RETRY"
            return self._feedback(UNKNOWN, self.calibration_error, "CAL", pose)
        self.base_torso = median(torsos)
        self.base_upper = median(uppers)
        self.calibrated = True
        self.needs_home = True
        return self._feedback(UNKNOWN, "CALIBRATED - BEGIN WHEN READY", "START", pose)

    def _lose_tracking(self, pose: ArmPose) -> Feedback:
        self.needs_home = True
        self.phase = "READY"
        self.bad_since.clear()
        self.angles.clear()
        self.torso_angles.clear()
        self.upper_angles.clear()
        self.rep_bad = False
        self.rep_start_ms = None
        return self._feedback(UNKNOWN, pose.reason, "TRACK", pose)

    def evaluate(self, pose: ArmPose, ms: int) -> Feedback:
        if self.calibrating:
            return self._calibration(pose, ms)
        if not pose.valid:
            if self.missing_since_ms is None:
                self.missing_since_ms = ms
            # UNKNOWN immediately; don't destroy rep progress for a 1-frame
            # webcam dropout. Extended gaps require returning to START.
            if ms - self.missing_since_ms >= 500:
                return self._lose_tracking(pose)
            return self._feedback(UNKNOWN, pose.reason, "TRACK", pose)
        if self.missing_since_ms is not None:
            if ms - self.missing_since_ms >= 500:
                self._lose_tracking(pose)
            self.missing_since_ms = None
        if not self.calibrated:
            return self._feedback(UNKNOWN, self.calibration_error or "PRESS C TO CALIBRATE", "CAL", pose)

        # Three-frame median filters remove a single-frame joint spike while
        # retaining responsiveness at ordinary webcam frame rates.
        for history, value in ((self.angles, pose.elbow_deg),
                               (self.torso_angles, pose.torso_deg),
                               (self.upper_angles, pose.upper_arm_deg)):
            history.append(value)
            if len(history) > 3:
                history.pop(0)
        angle = median(self.angles)
        progress = self._progress(angle)
        torso_change = abs(median(self.torso_angles) - self.base_torso)
        upper_change = abs(median(self.upper_angles) - self.base_upper)

        # First see the correct start position after calibration / tracking loss.
        if self.needs_home:
            if not self._home(angle):
                return self._feedback(UNKNOWN, "RETURN ARM TO START POSITION", "START",
                                      pose, progress, torso_change, upper_change, angle)
            self.needs_home = False
            self.phase = "READY"
            return self._feedback(UNKNOWN, "READY - START YOUR REP", "START", pose,
                                  progress, torso_change, upper_change, angle)

        # Thresholds depend on mode; both measured relative to calibration.
        lean_limit = 14 if self.exercise == "curl" else 12
        upper_limit = 24 if self.exercise == "curl" else 18
        candidates = {
            "LEAN": torso_change >= lean_limit,
            "ARM": upper_change >= upper_limit,
        }
        flagged = []
        for name, condition in candidates.items():
            if not condition:
                self.bad_since.pop(name, None)
            else:
                self.bad_since.setdefault(name, ms)
                if ms - self.bad_since[name] >= self.warning_hold_ms:
                    flagged.append(name)

        # Apply any warning to the ACTIVE rep before a completion is counted.
        # Otherwise a warning on the final return frame could be counted as good.
        if flagged and self.phase != "READY":
            self.rep_bad = True

        # Detect both the positive phase and return phase of a complete repetition.
        if self.exercise == "curl":
            if self.phase == "READY" and angle <= 130:
                self.phase = "CURLING"
                self.rep_bad = bool(flagged)
                self.rep_start_ms = ms
            elif self.phase == "CURLING":
                if angle <= 95:
                    self.phase = "LOWERING"
                elif angle >= 150:
                    self._partial(ms, "BEND ELBOW FURTHER ON CURL")
            elif self.phase == "LOWERING" and angle >= 150:
                self._complete(ms)
        else:
            if self.phase == "READY" and angle >= 135:
                self.phase = "PUSHING"
                self.rep_bad = bool(flagged)
                self.rep_start_ms = ms
            elif self.phase == "PUSHING":
                if angle >= 160:
                    self.phase = "RETURNING"
                elif angle <= 115:
                    self._partial(ms, "EXTEND ELBOW MORE ON PUSHDOWN")
            elif self.phase == "RETURNING" and angle <= 115:
                self._complete(ms)

        if flagged:
            primary = flagged[0]
            return self._feedback(BAD, "STOP TORSO SWINGING" if primary == "LEAN" else
                                  "KEEP UPPER ARM STEADY", primary, pose, progress,
                                  torso_change, upper_change, angle)

        if ms < self.issue_until:
            return self._feedback(BAD, self.last_message, self.last_issue, pose,
                                  progress, torso_change, upper_change, angle)

        active = self.phase != "READY" or ms-self.last_rep_ms < 1800
        if active:
            return self._feedback(GOOD, "MOVEMENT TRACKED - NO FLAGGED ISSUE", "OK",
                                  pose, progress, torso_change, upper_change, angle)
        return self._feedback(UNKNOWN, "READY - START YOUR REP", "IDLE", pose,
                              progress, torso_change, upper_change, angle)

    def _partial(self, ms: int, message: str) -> None:
        self.phase = "READY"
        self.rep_start_ms = None
        self.rep_bad = False
        self.issue_until = ms + 1600
        self.last_issue = "ROM"
        self.last_message = message

    def _complete(self, ms: int) -> None:
        # Reject implausibly fast or duplicate angle threshold crossings.
        # A complete curl/pushdown should take time, not just a few noisy frames.
        if (self.rep_start_ms is None or
                ms - self.rep_start_ms < self.min_rep_ms or
                ms - self.last_rep_ms < self.rep_cooldown_ms):
            self._partial(ms, "CONTROL THE MOVEMENT AND COMPLETE A FULL REP")
            return
        self.phase = "READY"
        self.rep_start_ms = None
        self.reps += 1
        self.last_rep_ms = ms
        if self.rep_bad:
            self.bad_reps += 1
            self.issue_until = ms + 1200
            self.last_issue = "FORM"
            self.last_message = "REP FINISHED WITH FORM WARNING"
        self.rep_bad = False
