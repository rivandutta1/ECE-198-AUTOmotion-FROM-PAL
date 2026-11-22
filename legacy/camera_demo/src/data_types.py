from dataclasses import dataclass

@dataclass
class Landmark:
    x: float
    y: float
    visibility: float

@dataclass
class PoseFrame:
    timestamp_ms: int
    valid: bool
    landmarks: dict[str, Landmark]