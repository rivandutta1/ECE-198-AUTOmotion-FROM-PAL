"""USB transport from laptop to Arduino; only GOOD/BAD/UNKNOWN messages.

The exact 115200-baud ASCII contract is: S,GOOD\n / S,BAD\n / S,UNKNOWN\n.
"""
import time

try:
    import serial
except ImportError:
    serial = None


VALID_STATUSES = {"GOOD", "BAD", "UNKNOWN"}


def packet(status: str) -> bytes:
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {status!r}")
    return f"S,{status}\n".encode("ascii")


class SerialLink:
    def __init__(self, port: str | None = None):
        self.connection = None
        if port:
            if serial is None:
                raise RuntimeError("Install pyserial: pip install pyserial")
            self.connection = serial.Serial(
                port=port, baudrate=115200, timeout=0, write_timeout=0.5
            )
            # Allow the Arduino USB connection/firmware to settle.
            time.sleep(2.0)

    def send(self, status: str) -> None:
        if self.connection:
            self.connection.write(packet(status))

    def close(self) -> None:
        if self.connection:
            self.connection.close()
