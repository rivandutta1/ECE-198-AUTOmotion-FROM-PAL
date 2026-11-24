"""serial_link.py: F packet format, input validation and Arduino port detection."""
from types import SimpleNamespace

import pytest

import serial_link
from serial_link import feedback_packet, find_arduino_port


def test_arm_packets():
    assert feedback_packet("curl", "GOOD", "OK", 3) == b"F,CURL,GOOD,OK,3\n"
    assert feedback_packet("PUSHDOWN", "BAD", "LEAN", 17) == b"F,PUSHDOWN,BAD,LEAN,17\n"
    assert feedback_packet("CURL", "UNKNOWN", "TRACK", 0) == b"F,CURL,UNKNOWN,TRACK,0\n"


@pytest.mark.parametrize("fields", [
    ("BENCH", "GOOD", "OK", 1),
    ("CURL", "EVIL", "OK", 1),
    ("CURL", "GOOD", "O\nK", 1),
    ("CURL", "GOOD", "OK", -1),
    ("CURL", "GOOD", "OK", 10000),
    ("CURL", "GOOD", "OK", True),
])
def test_invalid_packets_rejected(fields):
    with pytest.raises(ValueError): feedback_packet(*fields)


def test_autodetect_only_unambiguous_arduino(monkeypatch):
    def fake(device, desc, vid):
        return SimpleNamespace(device=device, description=desc, manufacturer="", vid=vid)
    class Ports:
        @staticmethod
        def comports():
            return [fake("/dev/cu.x", "Arduino Uno R4", 0x2341),
                    fake("/dev/cu.bluetooth", "Bluetooth", None)]
    monkeypatch.setattr(serial_link, "list_ports", Ports)
    assert find_arduino_port() == "/dev/cu.x"
    Ports.comports = lambda: [fake("/dev/cu.x", "Arduino", 0x2341),
                              fake("/dev/cu.y", "Arduino", 0x2341)]
    assert find_arduino_port() is None


def test_opening_the_port_does_not_block_and_waits_for_arduino_boot(monkeypatch):
    written = []
    class FakeSerial:
        def __init__(self, **kwargs):
            pass
        def write(self, data):
            written.append(data)
        def close(self):
            pass
    clock = [100.0]
    monkeypatch.setattr(serial_link, "serial", SimpleNamespace(Serial=FakeSerial))
    monkeypatch.setattr(serial_link.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(serial_link.time, "sleep",
                        lambda _s: pytest.fail("SerialLink must not sleep"))
    link = serial_link.SerialLink("/dev/fake")
    link.send_feedback("CURL", "GOOD", "OK", 1)
    assert written == []  # still booting
    clock[0] += serial_link.ARDUINO_STARTUP_S
    link.send_feedback("CURL", "GOOD", "OK", 2)
    assert written == [b"F,CURL,GOOD,OK,2\n"]


def test_press_packets_from_the_arduino():
    totals = serial_link.parse_press_packet("P,48213,CHEST,5,32\r")
    assert totals == serial_link.PressTotals("48213", "CHEST", 5, 32)
    for line in ("Chest ROM: 32", "P,48213,BENCH,5,32", "P,48213,CHEST,five,32",
                 "P,48213,CHEST,5", "F,CURL,GOOD,OK,3", ""):
        assert serial_link.parse_press_packet(line) is None


def test_read_lines_returns_only_complete_lines():
    class FakePort:
        chunks = [b"Switched modes\r\nP,1,CHEST,1,", b"20\r\nP,1,SHO", b""]
        @property
        def in_waiting(self):
            return len(self.chunks[0])
        def read(self, size):
            return self.chunks.pop(0)
    link = serial_link.SerialLink(None)
    link.connection = FakePort()
    assert link.read_lines() == ["Switched modes"]
    assert link.read_lines() == ["P,1,CHEST,1,20"]
    assert link.read_lines() == []  # "P,1,SHO" is still incomplete
