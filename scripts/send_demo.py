"""Manbir's Arduino-only test: cycles UNKNOWN / GOOD / BAD without a camera.

Usage: python scripts/send_demo.py --port COM3
"""
import argparse
import time
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.serial_link import SerialLink

parser = argparse.ArgumentParser()
parser.add_argument("--port", required=True)
args = parser.parse_args()

with_port = SerialLink(args.port)
try:
    for status in ("UNKNOWN", "GOOD", "BAD", "GOOD", "UNKNOWN"):
        print("Sending:", status)
        for _ in range(15):
            with_port.send(status)
            time.sleep(0.2)
    print("Done. Unplug or stop sending: Arduino should show CANNOT ASSESS.")
finally:
    with_port.close()
