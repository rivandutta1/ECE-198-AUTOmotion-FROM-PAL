# Cleanup map

Working notes for the cleanup. This file is removed at the end.

## Live execution path

```
main.py  main()
 ├─ argparse → validates options
 ├─ CameraWorker(args).start()          background thread: _run()
 │    ├─ camera_setup()                 cv2.VideoCapture (falls back to camera 0)
 │    ├─ src.vision.VisionTracker       MediaPipe Pose Landmarker (VIDEO mode)
 │    ├─ make_link() → src.serial_link  SerialLink + find_arduino_port()
 │    └─ loop:
 │         drain UI actions (mode/side/calibrate/reset/arduino/camera)
 │         cap.read() → tracking_frame() → tracker.process()
 │         src.app_modes.evaluate_monitor()
 │             → src.arm_exercises.measure_arm() → ArmExerciseMonitor.evaluate()
 │         every ≥0.2 s: SerialLink.send_feedback() → "F,EXERCISE,STATUS,ISSUE,REPS\n"
 │         publish an immutable Snapshot
 └─ UI loop on the main thread (target --ui-hz, default 60):
      worker.snapshot() → src.arm_ui.draw_screen() → cv2.imshow
      mouse clicks (hit_test) and keys → worker.send(action) / mirror / quit
```

Arduino side (`FROM-PAL/`, not modified): `loop()` → `motionUpdate()` →
`motionReadSerial()` → `motionParsePacket()`. The first packet switches the
board to DESKTOP mode, where `drawDesktopFeedback()` shows the exercise,
the status, and the rep count. Serial is one-way (Python → Arduino); Python
never reads what FROM-PAL prints.

## Files removed or archived (commit 1)

- Deleted: `docs/*` (setup notes for earlier UI versions),
  `Auto-motion/README.md` (contradicts the root README),
  `Auto-motion/.gitignore` (duplicate of the root one; its model rule is now
  `**/models/*.task` in the root file), and `tests/test_serial.py` (only
  tested the old `S,` packet).
- Archived in `legacy/` (see `legacy/README.md`): the old camera demo
  (`Auto-motion/main.py`, `camera.py`, `pose_tracker.py`, `data_types.py`,
  `form_rules.py`, `geometry.py`, `press_monitor.py`) with its three tests,
  plus both standalone U8g2 OLED sketches (`rivan_arduino.ino` and
  `arduino/auto_motion_display/`, renamed by version).

## Unused code inside live files

| File | Unused code | Why it's unused |
| --- | --- | --- |
| `main.py` | `EXERCISE_NAMES` import | Only `arm_ui.py` uses it. |
| `main.py` | UI FPS measurement (`previous_ui_frame`, `ui_fps`) | Passed to `draw_screen(fps=...)`, which ignores it. |
| `main.py` | Camera FPS measurement (`previous_frame_time`, `camera_fps`), `Snapshot.camera_fps`, `camera_resolution=(w, h)` | Same: `draw_screen` ignores `camera_fps` and `camera_resolution`. |
| `main.py` | `Snapshot.error` | Set when the worker crashes but never read; the error text already reaches the UI through `feedback.message`. |
| `arm_ui.py` | `draw_screen(fps, camera_resolution, camera_fps)` params; `_text(thick=)` param | Never drawn or used. |
| `arm_exercises.py` | `ArmExerciseMonitor.highest` / `.lowest` | Written on each rep, never read. |
| `serial_link.py` | `packet()`, `SerialLink.send()`, `VALID_EXERCISES` SHOULDER/CHEST | The app only sends `F,CURL…` / `F,PUSHDOWN…`. FROM-PAL rejects SHOULDER/CHEST anyway. |
| `app_modes.py` | Exercise check in `evaluate_monitor()`; side/exercise checks in `create_monitor()` | Repeated: `ArmExerciseMonitor.__init__` already validates both, and the worker only ever stores valid values. |
| `FROM-PAL` (not modified) | `S,<STATUS>` branch in `motionParsePacket`; the ISSUE field is validated but never displayed | Python never sends `S` packets. |

Kept on purpose: the extra `Feedback` fields (`bad_reps`, `stage`, angles,
`progress`, `confidence`). The UI doesn't show them, but the tests check
them and they describe the monitor's state.

## Hard-to-read code to simplify

- Python modules are hidden under `Auto-motion/src/`, which forces
  `sys.path` tricks in `main.py` and `pytest.ini`. Move them next to `main.py`.
- `CameraWorker._run()` is about 130 lines and mixes setup, UI action
  handling, and the frame loop. Split the action handling into a method.
- The same "keep calibration samples unless the gap is longer than 500 ms"
  block is copied three times in `ArmExerciseMonitor._calibration()`.
- `measure_arm()` builds the same message twice with `"RIGHT" if side ==
  "right" else "LEFT"` instead of using `side.upper()`.
- `app_modes.py`'s docstring still describes the press monitor.
- `requirements.txt` doesn't list NumPy, which `main.py` and `arm_ui.py`
  import directly.
