"""One-way USB serial link (115200 baud) to the FROM-PAL Arduino display.

Each packet is one ASCII line: F,<EXERCISE>,<STATUS>,<ISSUE>,<REPS>
e.g. F,CURL,GOOD,OK,2 or F,PUSHDOWN,BAD,LEAN,5
Only the values below are accepted, so no arbitrary text reaches the Arduino.
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
VALID_EXERCISES = {"CURL", "PUSHDOWN"}
VALID_ISSUES = {"OK", "TRACK", "CAL", "START", "IDLE", "LEAN", "ARM", "ROM", "FORM"}


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
