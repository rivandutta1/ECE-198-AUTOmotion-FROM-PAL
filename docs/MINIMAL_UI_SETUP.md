# AutoMotion — Minimal Pastel UI Update

This patch changes **only the UI presentation**, not the exercise scoring, camera worker, Arduino firmware, or 60 Hz target.

## Install

Make sure you've already installed the AutoMotion 60 Hz UI update. Move `AUTOMOTION_MINIMAL_PASTEL_UI.zip` into the root of your existing `auto-motion-tuesday` project and run:

```bash
unzip -o AUTOMOTION_MINIMAL_PASTEL_UI.zip -d .
.venv/bin/python -m pytest -q
```

Then double-click your existing `START_AUTO_MOTION.command`. If you've set `--camera 1` in that launcher, it will be preserved.

## What is visible now

* Four simple exercise selectors, right/left arm switch.
* Large mirrored webcam with uncluttered skeletal overlay.
* Form status and a single instruction at a time.
* Rep count **only for bicep curls and tricep pushdowns**; shoulder/chest rep counting was not implemented.
* Calibrate button near the status area; smaller secondary controls for reset, mirror, camera, Arduino, and exit.

The internal feedback still uses `GOOD`, `BAD`, and `UNKNOWN`. The Arduino still receives the same serial messages. The friendly labels `Good form`, `Check your form`, and `Calibration needed` do not change the underlying scoring.

Camera/pose processing remains separate from UI drawing. OpenCV aims for 60 Hz screen refresh but cannot guarantee actual display refresh on every system.
