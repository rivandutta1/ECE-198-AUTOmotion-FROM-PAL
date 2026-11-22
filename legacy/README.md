# Legacy code (archived, NOT used)

Nothing in this folder is used by the current AutoMotion app (`main.py` at the
repository root) or by the current Arduino firmware (`FROM-PAL/`). It is kept
for reference only. It is not maintained, and its tests are not part of the
main `pytest` run.

| Path | What it was | Replaced by |
| --- | --- | --- |
| `camera_demo/` | The first Python camera demo (`python main.py --mode shoulder` from inside this folder). Shoulder/chest press tracking with torso-lean rules (`form_rules.py`, `geometry.py`, `press_monitor.py`) and its own MediaPipe wrapper (`pose_tracker.py`, `data_types.py`). Its `--port` was never connected to a serial link. | Root `main.py` + `arm_exercises.py` (curl / pushdown) |
| `camera_demo/tests/` | Tests for the modules above. `test_press_monitor.py` relies on SHOULDER/CHEST serial packets, which the live `serial_link.py` no longer accepts. | — |
| `arduino/oled_display_v1_status_only/` | First standalone OLED sketch (U8g2 library, SSD1306 or SH1106). Shows only `S,GOOD` / `S,BAD` / `S,UNKNOWN`, which the app no longer sends. | `FROM-PAL/` |
| `arduino/oled_display_v2_arm_modes/` | Updated standalone OLED sketch (U8g2) that also understood `F,...` curl/pushdown packets. | `FROM-PAL/` (Adafruit SSD1306 + ultrasonic modes) |

To try the old camera demo anyway, run it from `legacy/camera_demo/` so
that its `src.` imports resolve. It expects its model at
`legacy/camera_demo/models/pose_landmarker_lite.task`.
