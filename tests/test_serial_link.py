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
