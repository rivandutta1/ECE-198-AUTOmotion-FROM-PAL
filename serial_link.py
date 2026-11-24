"""USB serial link (115200 baud) to the FROM-PAL Arduino.

App -> Arduino, one ASCII line per update: F,<EXERCISE>,<STATUS>,<ISSUE>,<REPS>
e.g. F,CURL,GOOD,OK,2 or F,PUSHDOWN,BAD,LEAN,5
Only the values below are accepted, so no arbitrary text reaches the Arduino.

Arduino -> app, whenever a handheld press total changes (and on connect):
P,<SESSION>,<SHOULDER|CHEST>,<REPS>,<MAX ROM CM>   e.g. P,48213,CHEST,5,32
Any other line the Arduino prints (debug messages) is ignored.
"""
from __future__ import annotations

from dataclasses import dataclass
import time

try:
    from serial.tools import list_ports
except ImportError:
    list_ports = None

try:
    import serial
except ImportError:
    serial = None

VALID_STATUSES = {"GOOD", "BAD", "UNKNOWN"}
VALID_EXERCISES = {"CURL", "PUSHDOWN"}
# Opening the port can reset the Arduino; it ignores serial input while it boots.
ARDUINO_STARTUP_S = 2.0

VALID_ISSUES = {"OK", "TRACK", "CAL", "START", "IDLE", "LEAN", "ARM", "ROM", "FORM"}


def feedback_packet(exercise: str, status: str, issue: str, reps: int) -> bytes:
    exercise = exercise.upper()
    if exercise not in VALID_EXERCISES or status not in VALID_STATUSES or issue not in VALID_ISSUES:
        raise ValueError("Invalid exercise/status/issue")
    if not isinstance(reps, int) or isinstance(reps, bool) or not 0 <= reps <= 9999:
        raise ValueError("Invalid rep count")
    return f"F,{exercise},{status},{issue},{reps}\n".encode("ascii")


PRESS_EXERCISES = ("SHOULDER", "CHEST")
MAX_LINE_BYTES = 256  # longer than any packet: a runaway line is dropped


@dataclass(frozen=True)
class PressTotals:
    """One handheld press's totals for one Arduino power-on session."""
    session: str
    exercise: str  # SHOULDER or CHEST
    reps: int
    rom_cm: int


def parse_press_packet(line: str) -> PressTotals | None:
    """Parse a P line from the Arduino; anything else (or invalid) -> None."""
    parts = line.strip().split(",")
    if len(parts) != 5 or parts[0] != "P" or parts[2] not in PRESS_EXERCISES:
        return None
    session, reps, rom = parts[1], parts[3], parts[4]
    if not (session.isdigit() and reps.isdigit() and rom.isdigit()):
        return None
    if len(session) > 10 or int(reps) > 99999 or int(rom) > 1000:
        return None
    return PressTotals(session, parts[2], int(reps), int(rom))


class SerialLink:
    def __init__(self, port: str | None = None):
        self.connection = None
        self._ready_at = 0.0
        self._incoming = b""
        if port:
            if serial is None:
                raise RuntimeError("Install pyserial: pip install pyserial")
            self.connection = serial.Serial(port=port, baudrate=115200,
                                            timeout=0, write_timeout=0.5)
            # Don't block the camera thread while the board boots: packets
            # sent before this time are skipped (a new one follows every 0.2 s).
            self._ready_at = time.monotonic() + ARDUINO_STARTUP_S

    def send_feedback(self, exercise: str, status: str, issue: str, reps: int) -> None:
        payload = feedback_packet(exercise, status, issue, reps)
        if self.connection and time.monotonic() >= self._ready_at:
            self.connection.write(payload)

    def read_lines(self) -> list[str]:
        """Complete lines the Arduino has sent since the last call (never blocks)."""
        if not self.connection:
            return []
        waiting = self.connection.in_waiting
        if waiting:
            self._incoming += self.connection.read(waiting)
        *lines, self._incoming = self._incoming.split(b"\n")
        if len(self._incoming) > MAX_LINE_BYTES:
            self._incoming = b""
        return [line.decode("ascii", "ignore").strip() for line in lines]

    def close(self) -> None:
        if self.connection:
            self.connection.close()
            self.connection = None


def find_arduino_port() -> str | None:
    """Return a port only when exactly one recognizable Arduino is attached.

    Never guess which USB serial device to open if more than one matches.
    """
    if list_ports is None:
        return None
    found = []
    try:
        ports = list_ports.comports()
    except Exception:
        return None
    for port in ports:
        description = f"{port.description or ''} {port.manufacturer or ''}".lower()
        vendor_id = getattr(port, "vid", None)
        if vendor_id in (0x2341, 0x2A03) or "arduino" in description or "uno r4" in description:
            if getattr(port, "device", None):
                found.append(port.device)
    unique = sorted(set(found))
    return unique[0] if len(unique) == 1 else None
