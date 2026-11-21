# Cleanup proposals

The current desktop app starts at the root [`main.py`](main.py). This review
uses the imports reachable from that entry point, the separate demo's imports,
the tests, and the sketches' supported packets. A file can sit outside the
desktop flow and still serve a teammate's demo, test, or hardware setup.
Confirm those uses before retiring anything.

## Older entry points and implementations

| Candidate | Evidence and likely reason it remains | Proposed change |
| --- | --- | --- |
| [`Auto-motion/main.py`](Auto-motion/main.py) and [`camera.py`](Auto-motion/src/camera.py) | This is a second CLI and camera loop. Its shoulder branch runs the earlier torso-lean detector. Its chest option falls through to the preview, and its parsed `--port` never reaches a serial link. The root launcher owns a separate worker, UI, and curl/pushdown monitor. The separate path appears to preserve a teammate's camera demo. | Confirm whether the demo is still used. If it is, label it clearly and give it a name that cannot be confused with the root launcher. Document its real shoulder and preview capabilities. If it is no longer needed, retire the entry point and camera loop together. |
| [`pose_tracker.py`](Auto-motion/src/pose_tracker.py), [`data_types.py`](Auto-motion/src/data_types.py), and [`vision.py`](Auto-motion/src/vision.py) | Both trackers call MediaPipe Pose Landmarker in VIDEO mode. The older one filters and converts landmarks into a named, pixel-based `PoseFrame` for the demo. The live tracker returns normalized landmarks and takes its model path from the root app. `data_types.py` is still imported by the legacy geometry module. | If the demo stays, share model construction and inference in `VisionTracker` and keep the pixel conversion in an adapter. Preserve the demo's confidence and coordinate behavior. If the demo is retired, remove its tracker and only remove the data types after resolving the geometry dependency. |
| [`press_monitor.py`](Auto-motion/src/press_monitor.py), [`form_rules.py`](Auto-motion/src/form_rules.py), and [`geometry.py`](Auto-motion/src/geometry.py) | `PressMonitor` has its own `Feedback`, range tracking, and warning logic. Its callers are tests. Its simpler torso rules are also used by the older camera demo. The live `ArmExerciseMonitor` has different exercise phases and calibration. Several angle calculations overlap, but the inputs and scoring rules differ. | Decide whether desktop shoulder/chest tracking is on the roadmap. If it is, either wire in a tested monitor deliberately or keep it clearly marked experimental. Share pure geometry only after checking coordinate and threshold behavior. If it is out of scope, archive the press monitor with its tests and retain any geometry/form code the demo still imports. |
| [`arduino/auto_motion_display/`](arduino/auto_motion_display) and [`rivan_arduino.ino`](rivan_arduino.ino) | Both are standalone U8g2 display sketches. The former supports legacy `S` and newer `F` packets. The latter only accepts `S` packets, which the current desktop loop does not send. The integrated [FROM-PAL firmware](FROM-PAL) adds physical modes and uses an Adafruit SSD1306 driver. The standalone sketches also offer an SH1106 build option, so they are only partial duplicates. | Treat FROM-PAL as the integrated target. Keep one explicitly labeled standalone alternative if someone still uses a U8g2 or SH1106 display. Confirm what boards are actually deployed before archiving the status-only sketch. |
| [Legacy serial helpers](Auto-motion/src/serial_link.py) | `packet()` and `SerialLink.send()` implement the old `S,STATUS` format. Repo tests still exercise `packet()` and the firmware still accepts it. The live worker calls `send_feedback()`, and its exercise list contains only curl and pushdown even though the generic encoder accepts shoulder and chest too. | Keep compatibility while older firmware or external tools rely on it. If those consumers are retired, shrink the format and exercise list in a coordinated change across the sender, retained parsers, and tests. |

## Small cleanup candidates in the live path

- The root app imports `EXERCISE_NAMES` without using it. Remove that import
  and retain the one in the dashboard, which uses it for display labels.
- `draw_screen()` accepts `fps`, `camera_resolution`, and `camera_fps` but
  draws none of them. The main loop still measures render FPS and the worker
  measures camera cadence to supply those arguments. The old UI setup notes
  describe visible diagnostics, which may explain those remnants. Either
  expose the measurements through an intentional debug feature or remove the
  unused arguments and measurement code together. Preserve the `--ui-hz`
  render scheduler and `--camera-fps` capture request.
- `ArmExerciseMonitor.highest` and `.lowest` track a rep's extrema, but
  completion is driven by angle thresholds and state transitions. There is no
  current reader for those extrema. Remove them if there are no consumers
  outside the checkout. Keep the threshold and rep-timing tests.
- NumPy is imported by the desktop app and UI, while
  [`requirements.txt`](requirements.txt) gets it indirectly through vision
  packages. Declare it as a direct dependency when refreshing the dependency
  list. Consider a separate development requirements file for pytest once the
  project has a stable setup on all three platforms.

## Repository and documentation

- [`Auto-motion/README.md`](Auto-motion/README.md) and the UI/setup notes in
  [`docs/`](docs) describe earlier states of the project. Some still assume
  a ZIP patch, a pastel dashboard, an absent I²C scanner, or a different OLED
  sketch. Keep historical notes where they explain decisions, label them as
  historical, and point users to the root README for installation.
- [`docs/test_results.md`](docs/test_results.md) is a shoulder-press physical
  test plan with results still pending. Rename or label it as a plan and
  record current curl/pushdown observations in a separate report if the team
  runs those checks.
- [`Auto-motion/.gitignore`](Auto-motion/.gitignore) largely duplicates the
  [root ignore rules](.gitignore). The nested `models/*.task` rule applies to
  the demo's local model location, while the root rule covers the live
  app's model directory. Preserve both locations if consolidating the ignore
  rules, and check the result with `git check-ignore`.
- A future package cleanup could move the active modules under one importable
  package and keep one public launcher. Do this after deciding the fate of
  the demo. Update the launcher, test paths, and any local shortcut together
  so the checkout continues to run without a manually set `PYTHONPATH`.

A low-risk first pass is to clarify the old setup notes and remove the
unused import. Confirm demo and display use with teammates before moving or
removing either implementation. After each cleanup, run the tests and smoke
test the current CLI, both exercises, and any retained demo or display.
