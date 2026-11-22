"""Experimental single-camera shoulder/chest press movement feedback.

This monitors *observable 2D cues*, not comprehensive/medical form.
Camera viewpoint and occlusion can make checks unavailable or misleading.
"""
from dataclasses import dataclass, field
from math import acos, atan2, degrees, hypot
from statistics import median
from typing import Optional

from src.form_rules import FormMonitor, GOOD, BAD, UNKNOWN
from src.geometry import PoseMeasurement, measure_pose

JOINTS = {
    "left": (11, 13, 15, 19, 23),
    "right": (12, 14, 16, 20, 24),
}

# All angles are projected 2D angles; these are unvalidated demo heuristics.
HOLD_MS = 700


def quality(p):
    if not (0.02 <= p.x <= 0.98 and 0.02 <= p.y <= 0.98):
        return False
    return all(getattr(p, k, 1.0) >= 0.6 for k in ("visibility", "presence"))


def joint_angle(a, vertex, b, w, h):
    x1, y1 = (a.x-vertex.x)*w, (a.y-vertex.y)*h
    x2, y2 = (b.x-vertex.x)*w, (b.y-vertex.y)*h
    denom = hypot(x1, y1) * hypot(x2, y2)
    if denom < 1e-6:
        return None
    return degrees(acos(max(-1.0, min(1.0, (x1*x2+y1*y2)/denom))))


def image_torso_angle(shoulder, hip, w, h):
    x = (shoulder.x - hip.x)*w
    y = (hip.y - shoulder.y)*h
    if hypot(x, y) < 60:
        return None
    return degrees(atan2(x, y))


def angular_change(a, b):
    return abs((a - b + 180.0) % 360.0 - 180.0)


def side_measurements(landmarks, side, w, h):
    if landmarks is None or len(landmarks) < 33 or min(w, h) <= 0:
        return None
    shoulder_i, elbow_i, wrist_i, index_i, hip_i = JOINTS[side]
    shoulder, elbow, wrist, hip = [landmarks[i] for i in (shoulder_i, elbow_i, wrist_i, hip_i)]
    if not all(quality(p) for p in (shoulder, elbow, wrist, hip)):
        return None
    torso = image_torso_angle(shoulder, hip, w, h)
    elbow_deg = joint_angle(shoulder, elbow, wrist, w, h)
    arm_torso_deg = joint_angle(hip, shoulder, elbow, w, h)
    if torso is None or elbow_deg is None or arm_torso_deg is None:
        return None
    index = landmarks[index_i]
    wrist_deg = joint_angle(elbow, wrist, index, w, h) if quality(index) else None
    torso_len = hypot((shoulder.x-hip.x)*w, (shoulder.y-hip.y)*h)
    return {
        "shoulder": shoulder, "elbow": elbow, "wrist": wrist,
        "elbow_deg": elbow_deg, "arm_torso_deg": arm_torso_deg,
        "wrist_deg": wrist_deg, "torso_deg": torso,
        "torso_len": torso_len,
        "wrist_to_shoulder": hypot((wrist.x-shoulder.x)*w, (wrist.y-shoulder.y)*h)/torso_len,
    }


@dataclass(frozen=True)
class Feedback:
    status: str
    detail: str
    issue: str = "NONE"       # short code sent to OLED
    deviation_deg: Optional[float] = None
    checks: dict = field(default_factory=dict)
    baseline_deg: Optional[float] = None


class TimedWarnings:
    """Debounce transient 2D pose noise; no warning until persistence."""
    def __init__(self, hold_ms=HOLD_MS):
        self.since = {}
        self.hold_ms = hold_ms

    def evaluate(self, flags, ms):
        for name in list(self.since):
            if not flags.get(name):
                del self.since[name]
        active = []
        for name, fails in flags.items():
            if not fails:
                continue
            first = self.since.setdefault(name, ms)
            if ms-first >= self.hold_ms:
                active.append(name)
        return active

    def reset(self):
        self.since.clear()


class RangeTracker:
    """Judge projected elbow excursion for a completed extension phase.

    Until a recognizable repetition occurs, ROM is UNTESTED. The displayed
    result is deliberately not a claim of full real-world range of motion.
    """
    def __init__(self, bottom_limit, top_limit, min_excursion=35):
        self.bottom_limit = bottom_limit
        self.top_limit = top_limit
        self.min_excursion = min_excursion
        self.reset()

    def reset(self):
        self.in_cycle = False
        self.minimum = 180.0
        self.maximum = 0.0
        self.last_result = None
        self.last_result_at = -1

    def update(self, angle, ms):
        if angle < self.top_limit-10:
            if not self.in_cycle:
                self.minimum = angle
                self.maximum = angle
            self.in_cycle = True
        if self.in_cycle:
            self.minimum = min(self.minimum, angle)
            self.maximum = max(self.maximum, angle)
            if angle >= self.top_limit:
                self.last_result = (self.minimum <= self.bottom_limit
                                    and self.maximum-self.minimum >= self.min_excursion)
                self.last_result_at = ms
                self.in_cycle = False
        # Hold latest result briefly enough to see after a completed rep.
        return self.last_result if ms-self.last_result_at <= 2500 else None


class PressMonitor:
    def __init__(self, exercise="shoulder", side="left"):
        if exercise not in ("shoulder", "chest"):
            raise ValueError("exercise must be shoulder or chest")
        if side not in JOINTS:
            raise ValueError("side must be left or right")
        self.exercise = exercise
        self.side = side
        self.shoulder_lean = FormMonitor() if exercise == "shoulder" else None
        self.baseline_deg = None
        self.calibrating = False
        self.cal_samples = []
        self.cal_error = None
        self.warnings = TimedWarnings()
        # These are projected-angle heuristics, NOT validated ROM criteria.
        self.range = RangeTracker(bottom_limit=115 if exercise == "shoulder" else 110,
                                  top_limit=155, min_excursion=35)
        self.previous_angle = None
        self.moved = False
        self.rest_angle = None

    def start_calibration(self):
        self.warnings.reset()
        self.range.reset()
        self.previous_angle = None
        self.moved = False
        self.rest_angle = None
        if self.exercise == "shoulder":
            self.shoulder_lean.start_calibration()
        else:
            self.calibrating = True
            self.cal_samples = []
            self.baseline_deg = None
            self.cal_error = None

    def _chest_calibrate(self, side_data, ms):
        if not self.calibrating:
            if self.baseline_deg is None:
                return Feedback(UNKNOWN, self.cal_error or "SIT UPRIGHT - PRESS C TO CALIBRATE", "CAL")
            return None
        if side_data is None:
            self.cal_samples = []
            return Feedback(UNKNOWN, "MOVE BACK: SHOW SHOULDER / ELBOW / WRIST / HIP", "TRACK")
        # The seated chest press requires an approximately upright torso.
        # An extreme projected torso tilt usually indicates a wrong camera
        # view / lying position. This tolerance is a demonstration heuristic.
        if abs(side_data["torso_deg"]) > 55:
            self.cal_samples = []
            return Feedback(UNKNOWN, "SIT UPRIGHT: SHOW SHOULDER AND HIP", "CAL")
        self.cal_samples.append((ms, side_data["torso_deg"]))
        elapsed = ms-self.cal_samples[0][0]
        if elapsed < 1800 or len(self.cal_samples) < 12:
            return Feedback(UNKNOWN, "CALIBRATING: SIT UPRIGHT AND HOLD STILL", "CAL")
        angles = [v for _, v in self.cal_samples]
        self.calibrating = False
        self.cal_samples = []
        # Unwrap across -180 / +180 while checking seated torso stability.
        offsets = [((v - angles[0] + 180) % 360) - 180 for v in angles]
        if max(offsets) - min(offsets) > 8:
            self.cal_error = "MOVED: PRESS C AGAIN"
            return Feedback(UNKNOWN, self.cal_error, "CAL")
        self.baseline_deg = ((angles[0] + median(offsets) + 180) % 360) - 180
        self.rest_angle = side_data["elbow_deg"]
        # Chest calibration starts with bent elbows. Seed the ROM cycle so
        # the FIRST forward press can be assessed on reaching extension.
        if self.rest_angle < self.range.top_limit - 10:
            self.range.in_cycle = True
            self.range.minimum = self.rest_angle
            self.range.maximum = self.rest_angle
        return Feedback(UNKNOWN, "READY: PUSH FORWARD AND RETURN", "CAL",
                        baseline_deg=self.baseline_deg)

    def evaluate(self, landmarks, w, h, ms):
        selected = side_measurements(landmarks, self.side, w, h)
        other_side = "right" if self.side == "left" else "left"
        other = side_measurements(landmarks, other_side, w, h)
        if self.exercise == "shoulder":
            sample = measure_pose(landmarks, w, h, side=self.side)
            # Allow the lower pressing phase near shoulder height, but not a
            # fully lowered arm, to participate in torso assessment.
            if sample.valid and selected is not None:
                wrist, shoulder = selected["wrist"], selected["shoulder"]
                active = (wrist.y < shoulder.y + 0.09
                          and selected["elbow"].y < selected["shoulder"].y + 0.20)
                sample = PoseMeasurement(True, active, sample.torso_angle_deg,
                                         "ARM NOT IN PRESS POSITION" if not active else "TRACKING")
            lean_result = self.shoulder_lean.evaluate(sample, ms)
            self.baseline_deg = self.shoulder_lean.baseline_deg
            if lean_result.status == UNKNOWN:
                self.warnings.reset()
                self.range.reset()
                return Feedback(UNKNOWN, lean_result.detail, "CAL" if self.baseline_deg is None else "TRACK",
                                baseline_deg=self.baseline_deg)
            torso_deviation = lean_result.deviation_deg
        else:
            calibration = self._chest_calibrate(selected, ms)
            if calibration is not None:
                return calibration
            if selected is None:
                self.warnings.reset()
                self.range.reset()
                return Feedback(UNKNOWN, "POSE HIDDEN / OUT OF FRAME", "TRACK",
                                baseline_deg=self.baseline_deg)
            torso_deviation = angular_change(selected["torso_deg"], self.baseline_deg)
            if self.rest_angle is not None and abs(selected["elbow_deg"]-self.rest_angle) > 10:
                self.moved = True
            if not self.moved:
                return Feedback(UNKNOWN, "START CHEST PRESS MOVEMENT", "TRACK",
                                baseline_deg=self.baseline_deg)

        if selected is None:
            self.warnings.reset()
            self.range.reset()
            return Feedback(UNKNOWN, "REQUIRED JOINTS NOT VISIBLE", "TRACK",
                            baseline_deg=self.baseline_deg)

        elbow_angle = selected["elbow_deg"]
        rom = self.range.update(elbow_angle, ms)
        checks = {"torso_change": round(torso_deviation, 1),
                  "elbow_angle": round(elbow_angle, 1),
                  "rom": "UNTESTED" if rom is None else ("PASS" if rom else "FAIL")}
        # Seated chest torso shift is NOT a reliable proxy for back support or spinal alignment.
        # Shoulder torso lean is ALREADY debounced by the existing FormMonitor.
        # Chest torso movement uses our own debounce timer.
        flags = {"LEAN": torso_deviation >= 18.0} if self.exercise == "chest" else {}
        # Wrist/hand angle is a *rough projection*, not a joint biomechanics measure.
        # Check when pose's index-finger landmark is actually visible.
        if selected["wrist_deg"] is not None:
            checks["wrist_projection"] = round(selected["wrist_deg"], 1)
            flags["WRIST"] = (abs(180-selected["wrist_deg"]) > 65)
        else:
            checks["wrist_projection"] = "UNAVAILABLE"

        if self.exercise == "shoulder":
            # Lower phase: wrist should not be wildly forward/behind elbow
            # in the selected side-view projection.
            if elbow_angle < 135:
                diff = abs(selected["wrist"].x-selected["elbow"].x)*w / selected["torso_len"]
                checks["elbow_wrist_offset"] = round(diff, 2)
                flags["ELBOW"] = diff > 0.65
        else:
            # Seated chest press at ~30-45 deg from front/side: projected upper arm vs
            # torso (camera-sensitive proxy; NOT true 3D elbow flare).
            if elbow_angle <= 125:
                checks["arm_torso_projection"] = round(selected["arm_torso_deg"], 1)
                flags["ELBOW"] = selected["arm_torso_deg"] > 115

        if other is not None:
            discrepancy = abs(elbow_angle - other["elbow_deg"])
            checks["arm_angle_difference"] = round(discrepancy, 1)
            flags["ASYMMETRY"] = discrepancy > 30
        else:
            checks["arm_angle_difference"] = "UNAVAILABLE"

        # ROM is a result of the latest completed motion; hold it while visible.
        if rom is False:
            flags["ROM"] = True
        active_issues = self.warnings.evaluate(flags, ms)
        if self.exercise == "shoulder" and lean_result.status == BAD:
            active_issues.insert(0, "LEAN")
        if active_issues:
            issue = active_issues[0]
            descriptions = {
                "LEAN": "TORSO MOVEMENT TOO LARGE",
                "ELBOW": "ELBOW POSITION (2D) - CHECK",
                "WRIST": "WRIST/HAND ALIGNMENT - CHECK",
                "ASYMMETRY": "LEFT/RIGHT ARM MISMATCH",
                "ROM": "INCOMPLETE PROJECTED RANGE",
            }
            return Feedback(BAD, descriptions[issue], issue, torso_deviation,
                            checks, self.baseline_deg)
        return Feedback(GOOD, "NO FLAGGED 2D ISSUE (NOT FULL FORM)", "NONE",
                        torso_deviation, checks, self.baseline_deg)
