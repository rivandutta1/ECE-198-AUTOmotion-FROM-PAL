"""Run Qt without a screen during tests (no window pops up)."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
