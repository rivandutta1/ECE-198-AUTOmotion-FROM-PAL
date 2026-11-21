"""115200 baud USB messages to AUTO-MOTION OLED.

Legacy: S,GOOD\n / S,BAD\n / S,UNKNOWN\n
Arm modes: F,CURL,GOOD,OK,2\n or F,PUSHDOWN,BAD,LEAN,5\n
Only enum-like printable data is accepted; no arbitrary newlines.
"""
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
VALID_EXERCISES = {"CURL", "PUSHDOWN", "SHOULDER", "CHEST"}
VALID_ISSUES = {"OK", "TRACK", "CAL", "START", "IDLE", "LEAN", "ARM", "ROM", "FORM"}


def packet(status: str) -> bytes:
    """Original firmware packet, kept for teammates' existing tests/tools."""
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {status!r}")
    return f"S,{status}\n".encode("ascii")


def feedback_packet(exercise: str, status: str, issue: str, reps: int) -> bytes:
    exercise = exercise.upper()
    if exercise not in VALID_EXERCISES or status not in VALID_STATUSES or issue not in VALID_ISSUES:
        raise ValueError("Invalid exercise/status/issue")
    if not isinstance(reps, int) or isinstance(reps, bool) or not 0 <= reps <= 9999:
        raise ValueError("Invalid rep count")
    return f"F,{exercise},{status},{issue},{reps}\n".encode("ascii")


class SerialLink:
    def __init__(self, port: str | None = None):
        self.connection = None
        if port:
            if serial is None:
                raise RuntimeError("Install pyserial: pip install pyserial")
            self.connection = serial.Serial(port=port, baudrate=115200,
                                            timeout=0, write_timeout=0.5)
            time.sleep(2)

    def send(self, status: str) -> None:
        if self.connection:
            self.connection.write(packet(status))

    def send_feedback(self, exercise: str, status: str, issue: str, reps: int) -> None:
        payload = feedback_packet(exercise, status, issue, reps)
        if self.connection:
            self.connection.write(payload)

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
