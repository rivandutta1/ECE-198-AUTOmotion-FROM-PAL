# AutoMotion

AutoMotion is a desktop webcam app for bicep curls and tricep pushdowns. It
tracks one selected arm, estimates posture and elbow motion in 2D, and shows
form feedback and completed reps. The app runs locally and can optionally send
the same exercise, status, and rep count to a FROM-PAL OLED over USB. A webcam
and a graphical desktop session are enough to use the app.

Run [the root `main.py`](main.py) for the current app; the Arduino firmware is
in [`FROM-PAL/`](FROM-PAL). Older code that is no longer used is archived in
[`legacy/`](legacy). See the [repository map](#repository-map) for where
everything lives.

## Install and run the desktop app

Use **Python 3.11**, the version used by this project. Set up a new virtual
environment on each computer and run all commands from the repository root.
Install Git if you need to clone the project. The app is on the `main` branch.

```sh
git clone --branch main https://github.com/rivandutta1/auto-motion-tuesday.git
cd auto-motion-tuesday
```

**Already have the checkout?** Open a terminal in that folder and skip the
clone. The Pose Landmarker Lite model is downloaded separately and saved to
`models/pose_landmarker_lite.task`. Skip the download if you already have that
file. MediaPipe package availability depends on your OS and CPU architecture.
[MediaPipe Python setup](https://developers.google.com/edge/mediapipe/solutions/setup_python) · [Pose Landmarker models](https://developers.google.com/edge/mediapipe/solutions/vision/pose_landmarker#models)

### macOS

Open Terminal. If you need Python 3.11 and already use Homebrew, install it with
`brew install python@3.11`. Then run these commands from the repository root.
[Homebrew Python 3.11](https://formulae.brew.sh/formula/python@3.11)

```sh
python3.11 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
mkdir -p models
curl -fL https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task -o models/pose_landmarker_lite.task
.venv/bin/python main.py --exercise curl --camera 0
```

If macOS prompts for camera access, allow it for the app hosting your launch,
such as Terminal. You can change that permission under **System Settings →
Privacy & Security → Camera**. [Apple camera permissions](https://support.apple.com/guide/mac-help/control-access-to-the-camera-mchlf6d108da/mac)

### Fedora Workstation

From a terminal in your graphical desktop session, install Python 3.11 and
run the app. The commands below use regular Fedora Workstation with DNF.
[Fedora Python 3.11 package](https://packages.fedoraproject.org/pkgs/python3.11/python3.11/)

```sh
sudo dnf install python3.11 git curl
python3.11 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
mkdir -p models
curl -fL https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task -o models/pose_landmarker_lite.task
./main.py --exercise curl --camera 0
```

If importing OpenCV reports a missing `libGL.so.1`, install the Fedora GLX
library with `sudo dnf install libglvnd-glx`. If the camera fails, check that the
webcam appears under `/dev/video*` and that another camera app is closed.
[Fedora GLX package](https://packages.fedoraproject.org/pkgs/libglvnd/libglvnd-glx/)

### Windows

In PowerShell, check `py -3.11 --version`. If Python 3.11 is missing, install
64-bit Python 3.11 on an x64 PC. The python.org 3.11.9 release includes a Windows
x64 installer. Use the Python launcher and run the commands from the repository
root. Calling the environment's Python directly avoids needing to activate it.
[Python 3.11.9 installers](https://www.python.org/downloads/release/python-3119/) · [Python virtual environments](https://docs.python.org/3.11/library/venv.html)

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
New-Item -ItemType Directory -Force models | Out-Null
Invoke-WebRequest -Uri "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task" -OutFile "models\pose_landmarker_lite.task"
.\.venv\Scripts\python.exe main.py --exercise curl --camera 0
```

In Windows 11, open **Settings → Privacy & security → Camera** and allow desktop
apps to access the camera. [Windows camera permissions](https://support.microsoft.com/en-us/windows/privacy/manage-app-permissions-for-a-camera-in-windows)

### Use the app

1. Stand side-on to the camera with your selected shoulder, elbow, wrist, and
   hip visible. Select **Bicep curl** or **Tricep pushdown** and the arm you
   want to track.
2. Calibration is automatic; you don't need to touch the laptop. Get into the
   starting position (for a curl, let your arm hang straight down; for a
   pushdown, bend your elbow) and hold still for about 1.5 seconds until the
   app says it is calibrated. If you move too soon it simply tries again. It
   also recalibrates on its own after you switch exercise, arm, or camera, and
   after you've been out of view for 5 seconds (your rep counts are kept).
   **Calibrate** / `C` forces a fresh calibration and clears the reps, which is
   useful after moving the camera.
3. Move through the exercise and return to the starting position under
   control. The panel on the right shows your form, the next step, how far
   through the current rep you are, and the details: completed and flagged
   reps, rep stage, tracking confidence, elbow angle, and how far your torso
   and upper arm have moved from their calibrated position.
   **Reset reps** clears the counts and preserves your calibration.
   **Mirror** flips the preview and overlay together while keeping the selected
   anatomical arm the same. **Camera** tries other available indices from 0–3.

| Key | Action |
| --- | --- |
| `1` / `2` | Select curl / pushdown |
| `L` / `R` | Select left / right arm |
| `C` | Recalibrate now (also clears reps) |
| `M` | Toggle mirror preview |
| `Q` / `Esc` | Exit |

Use `main.py --help` with the environment's interpreter for all options. On
macOS and Linux, `./main.py` works from the repository root: its first line
runs it with `.venv/bin/python`. `python main.py` ignores that line, so other
ways of launching it are unaffected.
`--exercise pushdown` and `--side left` change the startup selections.
`--camera 1` requests index 1 and falls back to 0 if it cannot open.
`--debug-tracking` logs changes in the tracking or form decision.
`--tracking-width` controls the maximum inference frame width (default 960).
`--camera-width`, `--camera-height` and `--camera-fps` request 1280×720 at 30 FPS
by default. The camera driver may negotiate different settings. `--ui-hz`
changes the rendering target (default 60 Hz). To use `--model full`, download
the Full model separately and save it as `models/pose_landmarker_full.task`.
[Pose Landmarker model variants](https://developers.google.com/edge/mediapipe/solutions/vision/pose_landmarker#models)

### Troubleshooting

| Symptom | Check |
| --- | --- |
| Missing model error | Check the filename and put the `.task` file in `models/`, beside the root `main.py`. |
| A camera cannot open or stops delivering frames | Close other apps using it, check permissions, then relaunch with another `--camera` index. |
| No matching MediaPipe distribution | Check that the environment uses Python 3.11 for your OS and CPU and update pip before retrying. |
| HighGUI window errors | Run in a graphical desktop session with `opencv-contrib-python` from `requirements.txt`. Headless OpenCV wheels omit the window backend. |
| Stuck on calibration or moving into view | Check the selected arm, side-on framing, lighting, and the starting elbow position. Use `--debug-tracking` to see the current reason. |
| `Camera only` with optional USB hardware attached | Check the terminal for the connection error. Run `-m serial.tools.list_ports -v` with the environment's Python, then use `--port` if auto-detection is ambiguous. Close any serial monitor before reconnecting. |

Avoid installing a second OpenCV wheel into the same environment because those
packages share the `cv2` import. Recreate the environment from
`requirements.txt` if imports start failing after mixing packages.
[OpenCV package guidance](https://pypi.org/project/opencv-contrib-python/)

## How the live app works

```text
Camera → OpenCV frame → VisionTracker → normalized body landmarks
                                           ↓
                                  measure_arm → ArmPose
                                           ↓
                                  ArmExerciseMonitor
                                           ↓
                                       Feedback
                                    ↙            ↘
                     latest Snapshot → UI       SerialLink → optional OLED
```

**Capture and inference.** [`main.py`](main.py) parses the options and starts
a `CameraWorker` thread. The worker owns
the capture device, MediaPipe detector, exercise monitor, and optional serial
port. The worker keeps the original frame for the preview, shrinks wider
frames for inference while preserving aspect ratio, and supplies strictly
increasing millisecond timestamps. [`vision.py`](vision.py)
converts BGR to RGB and runs MediaPipe Pose Landmarker in VIDEO mode for one
person. It returns the first pose's normalized image landmarks or `None`.

**Measurement.** [`app_modes.py`](app_modes.py) validates the
exercise and arm, creates the monitor, and routes landmarks through
`measure_arm()` in [`arm_exercises.py`](arm_exercises.py).
Measurement checks landmark visibility, presence, framing, and limb size. It
can use the opposite hip when the selected hip is occluded. It scales positions
to pixels so angles account for the image aspect ratio. The resulting
`ArmPose` carries the elbow angle, torso tilt, upper-arm tilt, and confidence,
or a tracking failure with a reason.

**Calibration and scoring.** Whenever it isn't calibrated, the monitor treats
every frame as a calibration attempt. It gathers at least 1.5 seconds and 10
stable observations in the exercise's starting posture, and starts over by
itself if you moved. Being untracked for 5 seconds drops the calibration (but
not the rep counts) so it is redone when you come back. Median torso and
upper-arm angles become the session baseline. Three-frame medians smooth
movement, and torso or upper-arm deviations must persist for 400 ms before
they trigger a live warning. Tracking loss returns `UNKNOWN` immediately.
Gaps of roughly half a second require returning to the starting position
before a rep can resume.

| Exercise | Rep state transitions using the smoothed elbow angle |
| --- | --- |
| Curl | Ready at ≥150°, enters curling at ≤130°, reaches the top at ≤95°, completes after returning to ≥150°. |
| Pushdown | Ready at ≤115°, enters pushing at ≥135°, reaches extension at ≥160°, completes after returning to ≤115°. |

Partial range or implausibly fast motion can produce a warning without adding
a rep. A full rep with a form warning increments both the completed and flagged
counts, and the dashboard shows both. `GOOD` means tracked
movement without a flagged issue, `BAD` means a rule flagged the movement,
and `UNKNOWN` covers missing input, calibration, and waiting. These are
experimental 2D heuristics. Camera placement, occlusion, and movement affect
their accuracy.

**Rendering and controls.** The main thread alone runs the OpenCV window,
keyboard handling, and mouse hit tests. It renders the most recent `Snapshot`
even when the camera or inference is slower than the UI. A short lock protects
the snapshot reference and a queue carries commands back to the worker.
[`arm_ui.py`](arm_ui.py) builds the dark dashboard with Pillow,
NumPy, and OpenCV, placing the selected arm overlay in the fitted video
viewport. The finished 1600×900 dashboard is then resized with a smooth
filter to the size the window really shows, because OpenCV's own window
scaling makes text jagged. Fonts resolve through `AUTOMOTION_FONT_PATH`,
supported local fonts (Noto Sans or DejaVu Sans on Linux), and Pillow fallbacks. Metro Nova is optional and is not bundled.

**Optional output.** [`serial_link.py`](serial_link.py) opens
one recognized USB port or honors an explicit override. It sends newline-ended
ASCII like `F,CURL,GOOD,OK,3` at 115200 baud, with fields for exercise, status,
issue, and reps. The worker attempts a send about every 200 ms while processing
frames. The link is optional and the UI's connected indicator reports an open
port, without a firmware acknowledgment. Communication is one-way: the app
never reads from the Arduino. The FROM-PAL sketch consumes the
result in Desktop mode and has its own independent Shoulder and Chest modes.
Its button cycles through the modes. The first valid packet on a connection
selects Desktop. The Desktop screen shows the exercise, the status in large
text, a short explanation of the issue code just below it (for example `LEAN`
→ "Stop torso swinging"), and the rep count. It shows **NO CONNECTION**
after 1.2 seconds without valid feedback. The firmware and hardware libraries are
separate from the desktop app setup.

## Repository map

| Path | What it contains and where it runs |
| --- | --- |
| [`main.py`](main.py) | Desktop entry point. Parses options, runs the `CameraWorker` thread (camera, pose, monitor, serial) and the UI loop (window, mouse, keys). Run it from the repository root. |
| [`vision.py`](vision.py) | MediaPipe Pose Landmarker wrapper. The only module that imports MediaPipe. |
| [`app_modes.py`](app_modes.py) | The supported exercises and arms, plus `create_monitor()` / `evaluate_monitor()`. |
| [`arm_exercises.py`](arm_exercises.py) | `measure_arm()` turns landmarks into angles; `ArmExerciseMonitor` handles calibration, form warnings, and rep counting. No camera dependency. |
| [`arm_ui.py`](arm_ui.py) | Draws the dashboard and maps mouse clicks to actions (`hit_test`). |
| [`serial_link.py`](serial_link.py) | Builds `F,...` packets and finds and opens the Arduino USB port. |
| [`FROM-PAL/`](FROM-PAL) | Arduino firmware. `FROM-PAL.ino` handles the OLED, button, and independent ultrasonic Shoulder/Chest tracking with Wire and Adafruit libraries. `auto_motion_display.h` parses the app's serial packets and draws the Desktop view. |
| [`legacy/`](legacy) | Archived, unused code: the first camera demo with its shoulder/chest press rules and tests, and two earlier standalone OLED sketches. See [`legacy/README.md`](legacy/README.md). |
| [`requirements.txt`](requirements.txt), [`pytest.ini`](pytest.ini), [`tests/`](tests) | Python dependencies, test settings, and the automated tests for the app and the FROM-PAL protocol. |

OpenCV supplies camera I/O and HighGUI windows. MediaPipe supplies the pose
landmarks. NumPy holds the image arrays. Pillow renders the dashboard and
text, pySerial handles optional USB output, and pytest runs the tests.
The `models/` and `.venv/` directories are local setup outputs.

## Run tests

From the repository root, run `.venv/bin/python -m pytest -q` on macOS or
Fedora, or `.\.venv\Scripts\python.exe -m pytest -q` in PowerShell.
`pytest.ini` makes the root modules importable and runs only `tests/`.

No webcam, MediaPipe model, or Arduino is needed: the tests use synthetic
landmarks and fake hardware.

| Test file | What it checks |
| --- | --- |
| [`test_app_modes.py`](tests/test_app_modes.py) | Only curl and pushdown, on the left or right arm, can be monitored. |
| [`test_arm_measurement.py`](tests/test_arm_measurement.py) | `measure_arm()`: joint angles from landmarks, confidence and visibility limits, the opposite-hip fallback, and rejection of off-screen, overlapping, or missing joints. |
| [`test_exercise_monitor.py`](tests/test_exercise_monitor.py) | `ArmExerciseMonitor`: automatic calibration (holding still, correct start pose, retrying after movement, short dropouts, recalibrating after 5 s out of view), good and partial reps for both exercises, torso-lean and upper-arm warnings, rejection of too-fast or double-counted reps, and tracking loss. |
| [`test_dashboard_ui.py`](tests/test_dashboard_ui.py) | `arm_ui.py`: the dashboard renders for every status, exercise, and mirror setting; buttons are large and clickable; the overlay follows mirroring; every measurement is shown and fits in the panel. |
| [`test_serial_link.py`](tests/test_serial_link.py) | `serial_link.py`: `F` packet format, rejection of invalid values, Arduino port auto-detection, and that connecting doesn't block while the board boots. |
| [`test_camera_worker.py`](tests/test_camera_worker.py) | `main.py`: the worker thread with a fake camera, tracker, and Arduino (exercise/arm switching, camera fallback, packets sent), plus the UI rate and the downscaling of inference frames. |
| [`test_from_pal_protocol.py`](tests/test_from_pal_protocol.py) | Compiles the real `FROM-PAL` sketch for your computer with simulated Arduino hardware and feeds it packets made by `serial_link.py`: mode button, Desktop screen, timeouts, and malformed lines. Skipped if no `c++` compiler is installed. |
| [`landmark_helpers.py`](tests/landmark_helpers.py) | Not a test: builds the synthetic arm poses used by the measurement and monitor tests. |

Tests archived in `legacy/` are not run. Real camera accuracy, OS-specific
device behavior, and the physical OLED still need to be checked by hand.

## Project roles

- Karthik converts camera observations into form feedback.
- Manbir operates the camera and measures exercise movement.
- Rivan integrates form feedback with the OLED.
- Graham built FROM-PAL.
