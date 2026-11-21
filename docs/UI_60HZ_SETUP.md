# AutoMotion — responsive pastel interface

This patch changes only `main.py`, `src/arm_ui.py`, and adds two tests plus this guide.
It works with the prior AutoMotion Easy UI / Arm Studio code. Keep your existing
`src/arm_exercises.py`, `src/press_monitor.py`, `src/app_modes.py`, `src/vision.py`,
`src/serial_link.py`, Arduino firmware, and model files.

## Design goals

- AutoMotion **interface refresh target: 60 Hz**, independent of the webcam.
- Camera requests **30 FPS** by default, but actual FPS depends on hardware.
- Pose tracking runs on a separate background thread. It does not block buttons.
- Camera can supply ~24 FPS while the interface still redraws at up to 60 Hz;
  the same last processed video frame may be displayed for multiple UI frames.
- All HighGUI window calls stay on the macOS main thread.
- Pastel theme, mirrored webcam, large click targets, left/right arm and four
  exercises, calibration, Arduino reconnection.
- The interface shows independent **UI Hz** and **TRACK FPS** metrics.
- Arduino feedback packets and exercise form rules are unchanged.

## Install on your current Git branch

Keep your current Git history and any uncommitted changes safe before replacing
files. From your `auto-motion-tuesday` directory, ensure the patch ZIP is there:

```bash
unzip -o AUTOMOTION_60HZ_UI_PATCH.zip -d .
.venv/bin/python -m pytest -q
```

Run through the existing Finder launcher (`START_AUTO_MOTION.command`). Your
existing `--camera 1` launcher setting is retained because this patch does not
include or change the launcher.

Or run:

```bash
.venv/bin/python main.py --camera 1 --ui-hz 60 --camera-fps 30
```

For a slower camera:

```bash
.venv/bin/python main.py --camera 1 --camera-fps 24
```

The camera FPS request is not a guarantee and doesn't dictate the interface rate.
`--tracking-width 960` (default) is a compromise between landmark precision
and speed. If tracking becomes unreliable, try `--tracking-width 1280`; that
may decrease processing throughput.

## Performance and accuracy notes

The **60 Hz is a target, not a guarantee**: OpenCV HighGUI doesn't guarantee
60 Hz presentation/vsync on macOS, and CPU/render performance varies. Confirm
"UI Hz" in the app on the actual Mac. If it remains far below 60 despite a
30 FPS camera, a native UI toolkit (e.g. Qt) is the next architectural step.

Async UI makes controls responsive while MediaPipe runs; it does not mean pose
analysis or form classification occurs at 60 FPS. Repeating camera frames does
not increase the temporal precision or accuracy of form tracking. `GOOD` means
only that none of the prototype's 2D checks currently flagged a problem.
