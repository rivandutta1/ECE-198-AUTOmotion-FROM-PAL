# Karthik — AUTO-MOTION Geometry, Calibration, Form Rules and Validation

**Follow these steps in order.** Your work is mostly independent of the webcam and Arduino until Monday. The full starter code already exists; your job is to understand the math, confirm it behaves correctly, test real shoulder-press movements, and tune only if evidence warrants it.

**You own:** `src/geometry.py`, `src/form_rules.py`, `tests/test_geometry.py`, `tests/test_form_rules.py`, and `docs/test_results.md` (create this). Rivan owns the webcam; Manbir owns Arduino/serial. Your algorithm **does NOT count reps**.

## Scope and realistic time budget

| When | Goal | Estimated time |
|---|---|---:|
| **Sun Nov 8 evening** | Clone, run tests, understand torso-angle rule | 1–2 h |
| **Mon Nov 9 morning** | Verify calibration/hysteresis; test synthetic cases | 1–2 h |
| **Mon Nov 9 afternoon** | Run 20–30 controlled shoulder-press posture trials; log errors | 2–3 h |
| **Mon Nov 9 evening** | Change thresholds only if needed, commit, PR, demo support | 1 h |
| **Tue Nov 10** | Report what succeeded/failed; test one final trial | 20–30 min |

### K1. Join the shared GitHub repository (15–25 min)

1. Accept Rivan's GitHub collaborator invitation. Ask Rivan for the private link `https://github.com/<OWNER>/auto-motion-tuesday`.
2. Install [Git](https://git-scm.com/downloads), [Python 3.11](https://www.python.org/downloads/), and [VS Code](https://code.visualstudio.com/) if missing.
3. Open VS Code's terminal. Clone the repository (replace `OWNER_USERNAME`):

**Windows PowerShell:**

```powershell
git clone https://github.com/OWNER_USERNAME/auto-motion-tuesday.git
cd auto-motion-tuesday
git switch -c karthik/form-rules
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pytest -q
```

**Apple Silicon Mac Terminal:**

```bash
git clone https://github.com/OWNER_USERNAME/auto-motion-tuesday.git
cd auto-motion-tuesday
git switch -c karthik/form-rules
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pytest -q
```

**Intel Mac exception:** Current MediaPipe Python installation may be unsupported on Intel macOS. You do **not** need MediaPipe for this role. On Intel Mac, make a virtual environment with an available Python 3.11, install **only** `pytest`, and run `python -m pytest -q`. The geometry and form-rule modules use only Python's standard library. Rivan will run AI inference on the Windows demo laptop.

**Check:** The included test suite passes (`11 passed` in the original kit). If Python is using the wrong environment, select `.venv` interpreter in VS Code using **Python: Select Interpreter**.

**Why:** You can test logic without waiting for camera hardware, and all code can be shared through Git.

### K2. Understand exactly what the form rule measures (30–45 min)

Open `src/geometry.py` and `src/form_rules.py` in VS Code. The prototype is **side-view, one-person, one selected arm** only.

**Measured landmarks** (MediaPipe indices, fixed across the project):

| Joint | Left index | Right index |
|---|---:|---:|
| Shoulder | 11 | 12 |
| Elbow | 13 | 14 |
| Wrist | 15 | 16 |
| Hip | 23 | 24 |

In `geometry.py`, normalized landmark positions `(x,y)` are scaled by actual frame width/height to pixels before geometry. It computes torso angle relative to vertical:

`dx = (shoulder.x - hip.x) * width`  
`up = (hip.y - shoulder.y) * height`  
`torso_deg = atan2(dx, up) * 180 / pi`

A vertical torso gives approximately **0°**. The system compares the absolute difference between current torso angle and the **person's calibrated baseline**. It does NOT estimate muscle forces, clinical range of motion, or all errors in an overhead press.

`active` is true only when the selected **wrist is above the selected shoulder** by at least 2.5% of frame height. If the arm is down, the output is gray `UNKNOWN` / `WAITING FOR SHOULDER PRESS`, not a misleading green status.

**Why:** The project needs one defensible, measurable signal, not a claim of a general exercise-coaching AI.

### K3. Understand the calibration and three-state decisions (30–45 min)

Open `src/form_rules.py` and read `FormMonitor` line by line.

1. Before calibration: `UNKNOWN`.
2. On **C**: `start_calibration()` clears the old baseline and requests 1.8 seconds of valid, arm-down, stable torso readings.
3. It takes the median of those readings as the baseline. If the torso varies by more than 8° while collecting, calibration fails and the user must press **C** again.
4. During overhead activity: difference < 18° from the baseline stays `GOOD` (*no major lean detected*).
5. If difference >= 18° persists for **700 ms**, status becomes `BAD`.
6. To leave `BAD`, difference must fall to <= 11°. These two thresholds are **hysteresis**, reducing flicker.
7. Missing body landmarks, low visibility, arm down, or no calibration → `UNKNOWN`.

The threshold numbers **18°, 700 ms, 11°** are **engineering demo parameters**, NOT validated medical criteria. It is okay to change them based on test data, but document the old/new values and reason. Do not announce “safe form” merely because the algorithm outputs `GOOD`.

**Why:** You must understand how false alarms happen: noise, camera positioning, wrists out of frame, torso angle drift, and interpreting a side-view projection.

### K4. Verify the algorithm with the included automated tests (30–60 min)

From repository root:

**Windows:**

```powershell
.venv\Scripts\python.exe -m pytest -q
```

**Mac:**

```bash
.venv/bin/python -m pytest -q
```

Read each test in `tests/test_geometry.py` and `tests/test_form_rules.py`. They check:

- Upright shoulder-to-hip geometry yields ~0°.
- Wrist down means `active=False`.
- Missing/hidden wrist means invalid measurement.
- A visible tilted torso changes calculated angle.
- No calibration means gray/unknown.
- A brief large lean does **not** immediately warn.
- A sustained large lean **does** warn.
- Returning to baseline clears the warning.
- Unstable calibration is rejected.

**Add one test** for this edge case: a long period of invalid landmarks after a warning must clear it to `UNKNOWN`, not remain red forever. Implement it by copying an existing test's `m = calibrated()` setup and calling `evaluate(sample(valid=False), timestamp)`. Run the suite again.

**Why:** Offline tests catch mistaken state transitions before involving hardware. Don't change the serial protocol (`S,GOOD\n`, `S,BAD\n`, `S,UNKNOWN\n`).

### K5. Design a *repeatable* physical test, not a subjective demonstration (15 min)

Use the Windows camera laptop with Rivan (the last stage requires actual video). Position one **consenting adult teammate** sideways to camera. Keep head, **hip**, shoulder and overhead wrist in frame. **No weights**. Select arm using Rivan's `--side left/right` argument. Use the same position and camera angle throughout a test set.

1. Press **C** while upright, with arm down; stand still until calibrated.
2. Perform a shoulder-press movement while torso stays upright (or simply raise and lower the arm in an unloaded shoulder-press pattern).
3. Keep wrist overhead and deliberately introduce a **comfortable, clearly visible** torso lean. Don't intentionally strain your back to trigger a threshold.
4. Correct the torso lean and check the status clears.
5. Hide the wrist, move out of frame, then lower arm; verify `UNKNOWN`.
6. Repeat with the other side only after starting a new session and recalibrating.

Avoid having to force a dangerous pose. If the threshold is too severe for a safe demonstration, lower it to a test-appropriate value and clearly state it is an experimental threshold, then retest false positives.

### K6. Run documented test cases (2–3 h, Monday)

Create `docs/test_results.md` (plain Markdown). Copy the following template and replace each `PENDING` **only after running the test**:

| ID | Test | Expected | Actual | Pass? | Notes |
|---|---|---|---|---|---|
| T1 | Before calibration | UNKNOWN | PENDING | PENDING | |
| T2 | Upright arm raised, five trials | GOOD | PENDING | PENDING | |
| T3 | Comfortable large lean held 1 s, five trials | BAD if measured deviation crosses threshold | PENDING | PENDING | |
| T4 | Brief lean under 0.7 s, five trials | No sustained BAD | PENDING | PENDING | |
| T5 | Arm down/hidden wrist, five trials | UNKNOWN | PENDING | PENDING | |
| T6 | Return upright after BAD, five trials | GOOD | PENDING | PENDING | |
| T7 | Move during calibration | Retry calibration | PENDING | PENDING | |
| T8 | Rotate camera/person relative to baseline | Recalibration needed | PENDING | PENDING | |

Record which side and approximate distance were used. If a trial did not physically cross 18°, mark **not a valid positive test**, not a failed detector. In your final write-up, distinguish *intended visible lean* from *actual measured tilt*. Never invent accuracy percentages or claim a `GOOD` frame proves correct shoulder-press form.

**Suggested acceptance for Tuesday:** all 3 states can be triggered reliably in repeated safe tests on the intended Windows machine; at least five upright/no-warning trials and five sustained-lean/warning trials, plus an invalid-tracking test. Treat this as a school-project test threshold, not clinical validation.

### K7. Tune only if justified; keep a record (30–45 min)

If Rivan reports unstable warnings, first try:

1. Keep the camera **still** and perpendicular to the movement plane.
2. Use consistent body distance and lighting.
3. Make sure the calibrated shoulder/hip are visible at all times.
4. Calibrate at rest with a stable upright torso.
5. Verify the tested deviation in degrees.
6. Only then adjust values in `FormMonitor.__init__()` in `src/form_rules.py`:
   - `warning_deg=18.0` — how much torso lean triggers a candidate warning.
   - `warning_hold_ms=700` — how long it must continue.
   - `clearing_deg=11.0` — how far to return to clear the warning.

If changed, ensure `clearing_deg < warning_deg`, update tests and `docs/test_results.md`, then rerun:

```powershell
.venv\Scripts\python.exe -m pytest -q
```

On macOS use `.venv/bin/python -m pytest -q`. Share any threshold changes with Rivan before Monday integration; the UI and presentation descriptions must use the values actually tested.

### K8. Publish and hand off your work (20–30 min)

From your own branch, after you finish tests and notes:

```bash
git status
git add src/geometry.py src/form_rules.py tests/test_geometry.py tests/test_form_rules.py docs/test_results.md
git commit -m "Validate shoulder-press torso-lean rule"
git push -u origin karthik/form-rules
```

Open a GitHub pull request from `karthik/form-rules` into `main`. Ask Rivan to review and merge it. Do not use `git push --force`; don't edit Manbir's Arduino firmware or Rivan's camera files without coordination.

Before Tuesday, show the team the test table and say explicitly which warnings are tested and which are not. **No rep counting is included.**

## Your completion checklist

- [ ] Repo cloned, branch made, offline tests run.
- [ ] Understand normalized landmark positions and the pixel-scaled torso angle.
- [ ] Understand calibration and state transitions.
- [ ] At least one additional automated failure/recovery test added.
- [ ] Physical good/large-lean/unknown trials run and logged.
- [ ] Threshold changes, if any, justified by repeatable results.
- [ ] PR reviewed and merged by Monday evening.
- [ ] Demonstration limitations stated accurately.

## Learn more

[Python math.atan2](https://docs.python.org/3/library/math.html#math.atan2) · [pytest quickstart](https://docs.pytest.org/en/stable/getting-started.html) · [MediaPipe pose landmarks](https://developers.google.com/edge/mediapipe/solutions/vision/pose_landmarker)
