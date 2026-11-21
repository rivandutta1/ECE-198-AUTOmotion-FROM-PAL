# AutoMotion

AutoMotion is a desktop webcam app for bicep curls and tricep pushdowns. It
tracks one selected arm, estimates posture and elbow motion in 2D, and shows
form feedback and completed reps. The app runs locally and can optionally send
the same exercise, status, and rep count to a FROM-PAL OLED over USB. A webcam
and a graphical desktop session are enough to use the app.

Run [the root `main.py`](main.py) for the current app. There is also an older
[shoulder camera demo](Auto-motion/main.py) with its own entry point. See the
[repository map](#repository-map) for where each implementation fits and
[unnessesary.md](unnessesary.md) for proposed cleanup.

## Install and run the desktop app

Use **Python 3.11**, the version used by this project. Set up a new virtual
environment on each computer and run all commands from the repository root.
Install Git if you need to clone the project. The curl and pushdown app is on
the `karthik/arm-exercises` branch in this repository.

```sh
git clone --branch karthik/arm-exercises https://github.com/rivandutta1/auto-motion-tuesday.git
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
.venv/bin/python main.py --exercise curl --camera 0
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
2. Click **Calibrate**. For a curl, let your arm hang straight down. For a
   pushdown, bend your elbow to the starting position. Hold still until the app
   says it is ready. Recalibrate after moving the camera or changing exercises
   or arms.
3. Move through the exercise and return to the starting position under
   control. **Reset reps** clears the counts and preserves your calibration.
   **Mirror** flips the preview and overlay together while keeping the selected
   anatomical arm the same. **Camera** tries other available indices from 0–3.

| Key | Action |
| --- | --- |
| `1` / `2` | Select curl / pushdown |
| `L` / `R` | Select left / right arm |
| `C` | Calibrate |
| `M` | Toggle mirror preview |
| `Q` / `Esc` | Exit |

Use `main.py --help` with the environment's interpreter for all options.
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

**Capture and inference.** [`main.py`](main.py) resolves the repository root
and adds `Auto-motion/` to Python's import path. Its `CameraWorker` owns
the capture device, MediaPipe detector, exercise monitor, and optional serial
port. The worker keeps the original frame for the preview, shrinks wider
frames for inference while preserving aspect ratio, and supplies strictly
increasing millisecond timestamps. [`vision.py`](Auto-motion/src/vision.py)
converts BGR to RGB and runs MediaPipe Pose Landmarker in VIDEO mode for one
person. It returns the first pose's normalized image landmarks or `None`.

**Measurement.** [`app_modes.py`](Auto-motion/src/app_modes.py) validates the
exercise and arm, creates the monitor, and routes landmarks through
`measure_arm()` in [`arm_exercises.py`](Auto-motion/src/arm_exercises.py).
Measurement checks landmark visibility, presence, framing, and limb size. It
can use the opposite hip when the selected hip is occluded. It scales positions
to pixels so angles account for the image aspect ratio. The resulting
`ArmPose` carries the elbow angle, torso tilt, upper-arm tilt, and confidence,
or a tracking failure with a reason.

**Calibration and scoring.** The monitor gathers at least 1.5 seconds and 10
stable observations in the exercise's starting posture. Median torso and
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
counts. The current dashboard displays completed reps. `GOOD` means tracked
movement without a flagged issue, `BAD` means a rule flagged the movement,
and `UNKNOWN` covers missing input, calibration, and waiting. These are
experimental 2D heuristics. Camera placement, occlusion, and movement affect
their accuracy.

**Rendering and controls.** The main thread alone runs the OpenCV window,
keyboard handling, and mouse hit tests. It renders the most recent `Snapshot`
even when the camera or inference is slower than the UI. A short lock protects
the snapshot reference and a queue carries commands back to the worker.
[`arm_ui.py`](Auto-motion/src/arm_ui.py) builds the dark dashboard with Pillow,
NumPy, and OpenCV, placing the selected arm overlay in the fitted video
viewport. Fonts resolve through `AUTOMOTION_FONT_PATH`, supported local fonts,
and Pillow fallbacks. Metro Nova is optional and is not bundled.

**Optional output.** [`serial_link.py`](Auto-motion/src/serial_link.py) opens
one recognized USB port or honors an explicit override. It sends newline-ended
ASCII like `F,CURL,GOOD,OK,3` at 115200 baud, with fields for exercise, status,
issue, and reps. The worker attempts a send about every 200 ms while processing
frames. The link is optional and the UI's connected indicator reports an open
port, without a firmware acknowledgment. The FROM-PAL sketch consumes the
result in Desktop mode and has its own independent Shoulder and Chest modes.
Its button cycles through the modes. The first valid packet on a connection
selects Desktop, and the Desktop screen shows **NO CONNECTION** after 1.2
seconds without valid feedback. The firmware and hardware libraries are
separate from the desktop app setup.

## Repository map

| Path | What it contains and where it runs |
| --- | --- |
| [`main.py`](main.py) | Current desktop entry point. Owns the worker, render loop, input bindings, and lifecycle. |
| [`Auto-motion/src/`](Auto-motion/src) | Shared source directory. The live app imports `app_modes.py`, `arm_exercises.py`, `arm_ui.py`, `serial_link.py`, and `vision.py`. |
| [`Auto-motion/main.py`](Auto-motion/main.py), [`camera.py`](Auto-motion/src/camera.py), [`pose_tracker.py`](Auto-motion/src/pose_tracker.py), [`data_types.py`](Auto-motion/src/data_types.py) | Separate older camera demo. It converts selected normalized landmarks to named pixel coordinates and overlays them on an OpenCV preview. Its shoulder path calls the older geometry and form rules. The chest choice has no matching evaluator in its camera loop, and the demo's parsed port is never passed to a serial connection. |
| [`geometry.py`](Auto-motion/src/geometry.py), [`form_rules.py`](Auto-motion/src/form_rules.py) | Earlier torso-lean pipeline. The demo calls `measure_pose_frame()` and `FormMonitor`. The normalized `measure_pose()` path also serves the experimental press monitor and tests. These modules sit outside the active curl and pushdown flow. |
| [`press_monitor.py`](Auto-motion/src/press_monitor.py) | Experimental shoulder/chest scoring with its own feedback, warning, and range tracking types. Exercised by tests. Neither Python CLI instantiates it. |
| [`FROM-PAL/`](FROM-PAL) | Current integrated firmware. `FROM-PAL.ino` handles the OLED, button, and independent ultrasonic tracking with Wire and Adafruit libraries. `auto_motion_display.h` parses serial feedback and draws the Desktop view. |
| [`arduino/auto_motion_display/`](arduino/auto_motion_display), [`rivan_arduino.ino`](rivan_arduino.ino) | Standalone U8g2 OLED sketches. The former accepts `F` and legacy `S` packets for a display-only setup. The latter is the status-only `S` prototype. Both are independent of the integrated FROM-PAL sketch. |
| [`docs/`](docs), [`Auto-motion/README.md`](Auto-motion/README.md) | Prior setup notes, UI iterations, an older demo overview, and a shoulder-press physical test plan. Some commands refer to old bundles, scripts, or sketches. Use this README for the current checkout. |
| [`requirements.txt`](requirements.txt), [`pytest.ini`](pytest.ini), [`tests/`](tests) | Python dependencies, the test import paths, and automated checks for the desktop app, older press rules, and FROM-PAL protocol. |
| [`.gitignore`](.gitignore), [`Auto-motion/.gitignore`](Auto-motion/.gitignore) | Ignore rules for local models, recordings, environments, caches, and editor files. The two sets mostly overlap. |

OpenCV supplies camera I/O and HighGUI windows. MediaPipe supplies the pose
landmarks. NumPy is imported directly for image arrays and is currently
installed through the vision dependencies. Pillow renders the dashboard and
text, pySerial handles optional USB output, and pytest runs the tests.
The `models/` and `.venv/` directories are local setup outputs.

## Run tests

From the repository root, run `.venv/bin/python -m pytest -q` on macOS or
Fedora, or `.\.venv\Scripts\python.exe -m pytest -q` in PowerShell.
`pytest.ini` makes the root entry point and the nested `src` modules
importable for tests.

- Exercise and tracking tests use synthetic landmark sequences to check
  calibration, warnings, rep transitions, and recovery from missing landmarks.
- UI and worker tests check the rendered canvas, controls, and background
  pipeline with a fake camera, tracker, and serial link. Some filenames reflect
  older interface designs.
- Serial tests cover packet formatting, input validation, and port selection.
  The FROM-PAL integration test compiles the actual sketch as a host program
  against simulated Arduino APIs and feeds it Python-generated packets. It
  skips if a `c++` compiler is unavailable.
- Legacy geometry, form, and press tests preserve behavior for the older code.
  Real camera accuracy, OS-specific device behavior, and the physical OLED
  require separate checks.

## Project roles

- Karthik converts camera observations into form feedback.
- Manbir operates the camera and measures exercise movement.
- Rivan integrates form feedback with the OLED.
- Graham built FROM-PAL.
