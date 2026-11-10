"""Calibration + 3-state shoulder-press form warning for large torso lean.

These thresholds are demo-specific engineering guesses, NOT rehabilitation
standards and NOT a guarantee of safe/correct exercise form.
"""
from dataclasses import dataclass
from statistics import median
from typing import Optional

from src.geometry import PoseMeasurement

GOOD = "GOOD"
BAD = "BAD"
UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class Decision:
    status: str
    detail: str
    deviation_deg: Optional[float] = None


class FormMonitor:
    def __init__(self, warning_deg=18.0, clearing_deg=11.0,
                 warning_hold_ms=700, calibration_ms=1800):
        self.warning_deg = warning_deg
        self.clearing_deg = clearing_deg
        self.warning_hold_ms = warning_hold_ms
        self.calibration_ms = calibration_ms
        self.baseline_deg: Optional[float] = None
        self.calibrating = False
        self.samples: list[tuple[int, float]] = []
        self.warning_since_ms: Optional[int] = None
        self.warning_active = False
        self.calibration_error: Optional[str] = None

    def start_calibration(self) -> None:
        """User presses C while standing upright and not pressing."""
        self.baseline_deg = None
        self.calibrating = True
        self.samples = []
        self.calibration_error = None
        self.warning_since_ms = None
        self.warning_active = False

    def evaluate(self, sample: PoseMeasurement, timestamp_ms: int) -> Decision:
        if self.calibrating:
            if not sample.valid or sample.torso_angle_deg is None:
                self.samples = []
                return Decision(UNKNOWN, "CALIBRATION: SHOW SHOULDER AND HIP")
            # Calibration must occur at rest, not during an overhead press.
            if sample.active:
                self.samples = []
                return Decision(UNKNOWN, "CALIBRATION: LOWER YOUR ARM")
            self.samples.append((timestamp_ms, sample.torso_angle_deg))
            elapsed = timestamp_ms - self.samples[0][0]
            if elapsed < self.calibration_ms or len(self.samples) < 12:
                return Decision(UNKNOWN, f"CALIBRATING {min(elapsed / 1000, 1.8):.1f}/1.8 S")
            angles = [angle for _, angle in self.samples]
            self.calibrating = False
            self.samples = []
            if max(angles) - min(angles) > 8.0:
                self.calibration_error = "CALIBRATION MOVEMENT: PRESS C AGAIN"
                return Decision(UNKNOWN, self.calibration_error)
            self.baseline_deg = median(angles)
            return Decision(UNKNOWN, "CALIBRATED: RAISE ARM TO PRESS")

        if self.baseline_deg is None:
            return Decision(UNKNOWN, self.calibration_error or "PRESS C TO CALIBRATE")
        if not sample.valid or sample.torso_angle_deg is None:
            self.warning_since_ms = None
            self.warning_active = False
            return Decision(UNKNOWN, sample.reason)
        if not sample.active:
            self.warning_since_ms = None
            self.warning_active = False
            return Decision(UNKNOWN, "WAITING FOR SHOULDER PRESS")

        deviation = abs(sample.torso_angle_deg - self.baseline_deg)
        if deviation <= self.clearing_deg:
            self.warning_active = False
            self.warning_since_ms = None
        elif deviation >= self.warning_deg and not self.warning_active:
            if self.warning_since_ms is None:
                self.warning_since_ms = timestamp_ms
            elif timestamp_ms - self.warning_since_ms >= self.warning_hold_ms:
                self.warning_active = True
        elif not self.warning_active:
            self.warning_since_ms = None

        if self.warning_active:
            return Decision(BAD, "LARGE SUSTAINED TORSO LEAN", deviation)
        return Decision(GOOD, "NO LARGE LEAN DETECTED", deviation)
