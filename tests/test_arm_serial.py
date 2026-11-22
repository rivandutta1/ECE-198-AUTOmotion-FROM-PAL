import pytest

from serial_link import feedback_packet, packet


def test_legacy_wire_format_unchanged():
    assert packet("GOOD") == b"S,GOOD\n"


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
