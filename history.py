"""Saved workout history: one plain text file, one line per entry.

Camera sets (written when a set ends: switching exercise/arm, Reset reps,
recalibrating with C, changing camera, or closing the app):

    2026-11-24 14:03 | Bicep curl | right arm | 12 reps | 2 flagged

Handheld presses: one line per exercise per Arduino power-on ("session"),
rewritten in place as its reps and max range of motion grow:

    2026-11-24 14:05 | Chest press | 5 reps | max ROM 32 cm | session 48213

The file is meant to be read by people too; lines this module can't parse
(e.g. hand-written notes) are kept and ignored.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path

from app_modes import EXERCISE_NAMES

DEFAULT_PATH = Path(__file__).resolve().parent / "data" / "history.txt"
PRESS_NAMES = {"SHOULDER": "Shoulder press", "CHEST": "Chest press"}
SEPARATOR = " | "
TIME_FORMAT = "%Y-%m-%d %H:%M"


@dataclass(frozen=True)
class CameraSet:
    when: str
    exercise: str  # display name, e.g. "Bicep curl"
    arm: str  # "right" or "left"
    reps: int
    flagged: int


@dataclass(frozen=True)
class PressSession:
    when: str  # last update
    exercise: str  # display name, e.g. "Chest press"
    reps: int
    rom_cm: int
    session: str


def _now():
    return datetime.now().strftime(TIME_FORMAT)


def format_entry(entry) -> str:
    if isinstance(entry, CameraSet):
        fields = (entry.when, entry.exercise, f"{entry.arm} arm",
                  f"{entry.reps} reps", f"{entry.flagged} flagged")
    else:
        fields = (entry.when, entry.exercise, f"{entry.reps} reps",
                  f"max ROM {entry.rom_cm} cm", f"session {entry.session}")
    return SEPARATOR.join(fields)


def _number(text, prefix="", suffix=""):
    """'12 reps' with suffix ' reps' -> 12; None if it doesn't match."""
    if not (text.startswith(prefix) and text.endswith(suffix)):
        return None
    digits = text[len(prefix):len(text) - len(suffix)]
    return int(digits) if digits.isdigit() else None


def parse_line(line: str):
    """A CameraSet or PressSession, or None for anything else."""
    fields = [field.strip() for field in line.strip().split("|")]
    if len(fields) != 5:
        return None
    when, exercise = fields[0], fields[1]
    if exercise in EXERCISE_NAMES.values() and fields[2].endswith(" arm"):
        reps, flagged = _number(fields[3], suffix=" reps"), _number(fields[4], suffix=" flagged")
        if reps is not None and flagged is not None:
            return CameraSet(when, exercise, fields[2][:-4], reps, flagged)
    if exercise in PRESS_NAMES.values():
        reps = _number(fields[2], suffix=" reps")
        rom = _number(fields[3], prefix="max ROM ", suffix=" cm")
        session = fields[4][len("session "):] if fields[4].startswith("session ") else ""
        if reps is not None and rom is not None and session:
            return PressSession(when, exercise, reps, rom, session)
    return None


def _read_lines(path: Path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []


def load(path: Path = DEFAULT_PATH) -> list:
    """Every saved entry, newest first."""
    entries = [entry for entry in map(parse_line, _read_lines(path)) if entry]
    # Stable sort: within the same minute, the line written later comes first.
    return sorted(reversed(entries), key=lambda entry: entry.when, reverse=True)


def save_set(path: Path, exercise: str, arm: str, reps: int, flagged: int) -> None:
    """Append one finished camera set (exercise = 'curl' or 'pushdown')."""
    entry = CameraSet(_now(), EXERCISE_NAMES[exercise], arm, reps, flagged)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(format_entry(entry) + "\n")


def save_press(path: Path, session: str, exercise: str, reps: int, rom_cm: int) -> None:
    """Add or update the line for this press in this Arduino session
    (exercise = 'SHOULDER' or 'CHEST')."""
    entry = PressSession(_now(), PRESS_NAMES[exercise], reps, rom_cm, session)
    lines = _read_lines(path)
    for index, line in enumerate(lines):
        old = parse_line(line)
        if (isinstance(old, PressSession) and old.session == session
                and old.exercise == entry.exercise):
            lines[index] = format_entry(entry)
            break
    else:
        lines.append(format_entry(entry))
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write a temporary file and swap it in, so a crash can't leave half a file.
    temporary = path.with_suffix(".tmp")
    temporary.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.replace(temporary, path)
