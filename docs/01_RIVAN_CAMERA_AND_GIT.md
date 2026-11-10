# Rivan — AUTO-MOTION Windows Camera + Git + Final Integration

**Read this from top to bottom.** Other members have their own guides: `02_KARTHIK_FORM_LOGIC_AND_TESTING.md` and `03_MANBIR_ARDUINO_AND_SERIAL.md`.

**You own:** the shared GitHub repository, working Windows camera laptop, MediaPipe model and webcam processing, main Python program, and Tuesday demonstration. All necessary starter code is already supplied. Your job is to **run, understand, test, fix, and integrate it**, not write the AI model from scratch.

## Tuesday's exact product and responsibilities

**Scope:** ONE side-view shoulder-press, ONE visible warning: sustained large torso lean relative to an upright baseline. Python outputs one of `GOOD`, `BAD`, `UNKNOWN`. The Arduino UNO R4 Minima receives this text over USB and displays the result. **NO rep counter, no camera training, no tracking multiple people, no FROM-PAL integration.** A monochrome Arduino OLED displays text; only the Windows webcam preview displays green/red/gray color.

You will demonstrate with **no weights** and consenting team members. `GOOD` means *no major torso lean detected by this limited rule*; it does **not** certify that exercise form is safe.

## Time budget and critical deadlines

| When (Toronto local time) | Your outcome | Approx. effort |
|---|---|---:|
| **Sunday Nov 8, evening** | Repository shared; Windows Python setup; camera tracking first run | 2–3 hours |
| **Monday Nov 9, morning** | Calibrated webcam changes status in real time | 1–2 hours |
| **Monday Nov 9, afternoon** | Send working status to Manbir's Arduino; resolve conflicts | 1–2 hours |
| **Monday Nov 9, by 9:00 PM** | Final code freeze, demo video/notes and backup | 1 hour |
| **Tuesday Nov 10** | Run the repeatable presentation demonstration | 30–45 minutes |

### R1. Make ONE GitHub repo and invite both teammates (about 30 min)

1. Download and unzip **`AUTO_MOTION_TUESDAY_KIT.zip`** on the Windows laptop. It should contain `main.py`, `src/`, `arduino/`, `scripts/`, `tests/`, `docs/`, and `requirements.txt`.
2. On [github.com/new](https://github.com/new), create a **private** repo named `auto-motion-tuesday`. Do **not** enable the GitHub README, `.gitignore`, or license checkboxes: the zip includes a README and `.gitignore`.
3. Open the **unzipped kit folder** in VS Code: **File → Open Folder**. Choose the directory that contains `main.py`, not the outer download folder.
4. Open **Terminal → New Terminal**. Run these commands (replace `YOUR_GITHUB_USERNAME` once):

```powershell
git --version
git init -b main
git add .
git commit -m "Add Tuesday AUTO-MOTION starter kit"
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/auto-motion-tuesday.git
git push -u origin main
```

5. If Git says your name/email is unset, set them once and repeat the commit:

```powershell
git config --global user.name "Your Name"
git config --global user.email "YOUR_GITHUB_EMAIL"
```

6. If GitHub asks you to sign in, use the browser/VS Code authentication flow. Do **not** put your password in code, Git commands, or a README.
7. On GitHub: repository **Settings → Collaborators → Add people**; invite Karthik and Manbir by their GitHub usernames. Ask them to accept.
8. Send **the private repo URL** and the two member-specific guide filenames. They should **clone**; do not email copies of the code as separate projects.
9. Create your branch:

```powershell
git switch -c rivan/camera
```

**Check:** The GitHub repository contains the files and both people can see it. If you already have a git repo in that folder, stop and check `git status` and `git remote -v` rather than re-running `git init`.

**Why:** This avoids three incompatible versions of the same prototype. Each person works in a different file group and requests a merge when ready.

### R2. Prepare the official Windows development setup (about 30–45 min)

1. Install **Python 3.11 64-bit** from [python.org](https://www.python.org/downloads/). In PowerShell, verify `py -3.11 --version`.
2. Install [VS Code](https://code.visualstudio.com/) and the Python extension by Microsoft.
3. Install [Git](https://git-scm.com/downloads) if step R1 indicated it was missing.
4. With `main.py` in the current directory, run **exactly**:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pytest -q
```

5. The included offline test suite should report `11 passed` (or a larger number if the team adds tests). If it fails, share the full error output with the relevant module owner before changing code.
6. In VS Code press **Ctrl+Shift+P**, choose **Python: Select Interpreter**, select `.venv\Scripts\python.exe`.
7. Keep `.venv/` out of Git; it is already listed in `.gitignore`.

**What you're learning:** Python virtual environments isolate dependencies; MediaPipe does inference; OpenCV handles video; Git stores source code, not your local installation.

**Why:** Developers on different operating systems can work with the same code; do not share or commit your `.venv` folder.

### R3. Download the pretrained AI model (10–20 min)

Run:

```powershell
.venv\Scripts\python.exe scripts\download_model.py
```

The script downloads Google's **Pose Landmarker Lite** model to `models/pose_landmarker_lite.task`. It is NOT included in Git; each camera-running machine downloads its own copy. The model detects body landmarks and runs locally, so there is no paid API or training step.

**Check:** The message says a model was saved and the `.task` file exists under `models/`. If downloading is blocked, use the [official model link](https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task) in the browser and save it under that precise filename.

### R4. Verify the webcam and live pose detection (45–90 min)

1. Check Windows **Settings → Privacy & security → Camera**, turn camera access on for desktop apps.
2. Close Teams, Zoom, or other apps using the camera.
3. Put the laptop at **torso height**, 2–3 metres from the test subject if space permits. Face your **side** toward the camera. The head/shoulders, **hip**, and raised **wrist** must fit in frame.
4. Start **camera-only mode** (no Arduino needed):

```powershell
.venv\Scripts\python.exe main.py --side left
```

5. You should see an OpenCV window with a live picture, a line through one shoulder/elbow/wrist/hip set, and a **gray `CANNOT ASSESS`** label.
6. Press **Q** to quit. If the arm shown is the wrong side or frequently disappears, restart with `--side right`.
7. If no video: try `--camera 1`; verify webcam access and close other camera apps. If `No module named ...`, use the `.venv` commands above.

**What you're learning:** `main.py` captures frames; `src/vision.py` runs MediaPipe's VIDEO inference with increasing timestamps; `src/geometry.py` uses four landmarks; `src/form_rules.py` decides the status; `src/serial_link.py` sends it to Arduino if enabled.

**Check:** Body tracking and all text stay responsive through 60 seconds. **Do not proceed to serial integration until this passes.**

### R5. Learn the controls and demonstrate the three statuses (45–60 min)

1. **Gray:** When first opened, `CANNOT ASSESS / PRESS C TO CALIBRATE` is expected.
2. Stand upright, with the selected arm **DOWN**, and make sure the selected shoulder, elbow, wrist and hip are clearly visible.
3. Press **C** inside the OpenCV window. Remain still and keep the arm down for **2 seconds**. The app records the torso's baseline tilt and reports `CALIBRATED` when it finishes.
4. Raise your selected arm so the wrist is **visibly higher than the shoulder**. Keep the torso near the original upright position. It should show **green `GOOD`**.
5. While the arm remains raised, slowly make a comfortable but visibly large torso lean **forward or backward in the plane visible from the side (so your torso slopes left/right in the video, not toward the webcam lens)** so it is clearly visible in the side view. Hold for about 1 second. When deviation reaches the current rule (18° for at least 700 ms), it should show **red `BAD`** and `LARGE SUSTAINED TORSO LEAN`.
6. Return upright. It should clear back to `GOOD` when the deviation falls below 11°.
7. Lower the arm, hide a required joint, or move partly out of frame. It should show **gray `CANNOT ASSESS`**, rather than pretending to know form quality.
8. Press **C** again any time you change camera angle or person. Recalibrate with arm down.

**If it's always gray:** Check the selected side and visibility of ALL four points, lower arm while calibrating, wait 2 seconds, then raise wrist above shoulder. The program deliberately does not assess when the exercise is inactive.

**If it turns red while upright:** Recalibrate while actually upright and still; ensure camera is stationary and person has not shifted in the frame.

**If it never turns red:** Verify the torso itself changes angle, not just the arm; record a test, ask Karthik to inspect the 18° threshold and measurement geometry. Do NOT change thresholds silently or claim universal clinical accuracy.

**Safety:** Use unloaded, comfortable movements; no need to force an extreme lean to trigger a demo. Threshold tuning can be done in code if the threshold is not practical or reliable.

### R6. Integrate Manbir's Arduino (30–60 min, Monday)

1. Make sure Manbir has confirmed the OLED shows all three statuses using `scripts/send_demo.py`. If not, **do not block camera development**.
2. Close **Arduino IDE Serial Monitor**. Uploading firmware and using Python serial usually cannot happen simultaneously on the same port.
3. In PowerShell, list serial ports:

```powershell
.venv\Scripts\python.exe -m serial.tools.list_ports
```

4. Use the actual printed port, e.g. `COM3` (this example is NOT guaranteed):

```powershell
.venv\Scripts\python.exe main.py --side left --port COM3
```

5. After Python opens the port, the screen should show `CANNOT ASSESS`; after calibration and the raised-arm test, `GOOD`; after sustained lean, `BAD`.
6. If Python says access denied, shut Arduino IDE Serial Monitor. If `COM3` doesn't exist, rerun port discovery and use the actual name.
7. The UNO R4 **only displays the status**. Python handles all pose analysis and timing. This design intentionally has **no rep counter**.

### R7. Git branch, reviews, and Monday code freeze (30–60 min)

Keep changes in your branch limited to `main.py`, `src/vision.py`, model downloader and integration notes. Share all interface changes before applying them. Create `docs/rivan_report.md` with a few dated sentences recording your Windows version, working webcam index/side, test outcomes, and demo steps. A small test report makes your branch useful even if the starter Python code required no edits. Then commit your changes:

```powershell
git status
git add main.py src/vision.py scripts/download_model.py docs/rivan_report.md
git commit -m "Verify camera pose preview and integration"
git push -u origin rivan/camera
```

On GitHub, open a **Pull request → base `main`, compare `rivan/camera`**. Have one teammate review before merging. Karthik and Manbir do likewise for their files. Once the pull requests are merged, on the Windows laptop:

```powershell
git switch main
git pull --ff-only origin main
.venv\Scripts\python.exe -m pytest -q
```

Run the full real-world demo again after the merges. If `git pull` reports local changes, run `git status` and commit or stash your changes; **do not reset or delete others' work**.

### R8. Presentation rehearsal and fallback (Monday evening)

Use this 60–90-second demonstration sequence:

1. Show the live side-view camera and the UNO R4 OLED (two viewpoints if needed).
2. `CANNOT ASSESS` before calibration.
3. Press **C** upright with arm down; wait for calibration.
4. Raise arm with upright torso → laptop **green `GOOD`**, OLED **GOOD**.
5. Show a deliberately obvious but comfortable torso deviation → laptop **red `BAD`**, OLED **BAD**.
6. Return upright → **GOOD**. Lower arm/obscure wrist → **CANNOT ASSESS**.
7. State that this is a **prototype warning for large torso lean**; it does not diagnose complete exercise form or assess patients.

Record evidence of the controlled test only with consent, and do not store patient videos. Save a short reproducible test log and working Git revision before the deadline. If the OLED is blocked by an unknown shield controller, still show a camera-only preview and state that Arduino screen integration is pending; do not claim a working display without hardware verification.

## Your completion checklist

- [ ] GitHub repo exists; teammates can clone it; separate branches used.
- [ ] Windows Python 3.11 `.venv` exists; offline tests pass.
- [ ] Official model downloaded and webcam runs with no Arduino.
- [ ] Side view and selected arm show stable landmarks.
- [ ] C calibrates the upright posture while arm is down.
- [ ] Green/Red/Gray states reproduced as described.
- [ ] Manbir's display receives real status packets over USB.
- [ ] Team's merged `main` runs before the Monday freeze.
- [ ] Demonstration rehearsed and truthful limitations documented.

## Verified external references

[MediaPipe Pose Landmarker Python](https://developers.google.com/edge/mediapipe/solutions/vision/pose_landmarker/python) · [Supported Python environments](https://developers.google.com/edge/mediapipe/solutions/setup_python) · [OpenCV webcam tutorial](https://docs.opencv.org/4.x/dd/d43/tutorial_py_video_display.html) · [GitHub create repository](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-new-repository)
