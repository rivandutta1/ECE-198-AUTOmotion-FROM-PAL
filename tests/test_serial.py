import pytest
from src.serial_link import packet


def test_packets():
    assert packet("GOOD") == b"S,GOOD\n"
    assert packet("BAD") == b"S,BAD\n"
    assert packet("UNKNOWN") == b"S,UNKNOWN\n"


def test_reject_incorrect_status():
    with pytest.raises(ValueError):
        packet("GREAT")
