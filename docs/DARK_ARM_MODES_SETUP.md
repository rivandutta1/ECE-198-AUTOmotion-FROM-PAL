# AutoMotion — Dark Curl / Pushdown Build

## What this patch changes

- The **only selectable exercise modes** are **bicep curl** and **tricep pushdown**. Both support left or right arm. Shoulder/chest buttons and CLI choices are removed. Older `src/press_monitor.py` is left untouched for compatibility with your teammates' historical tests, but the app does **not** import, launch, or display it.
- The dark UI shows: live mirrored video, exercise, selected arm, form status, one instruction, and completed reps. Calibration, reset, mirror, camera, Arduino connect, and exit buttons remain accessible without terminal commands.
- Uses your licensed **Metro Nova** font **if locally installed**. Otherwise uses a system sans-serif fallback. No font files are bundled or downloaded. If a licensed font file is already on your machine but is not auto-detected, set the `AUTOMOTION_FONT_PATH` environment variable to its full path.
- Runs independent 60 Hz-target UI updates (not guaranteed display sync) while the camera/MediaPipe worker can run at 24–30 FPS. UI caches each scaled camera preview until a new video frame arrives.
- Fixes a form-warning timing bug that could mark a rep good when the warning became active on the last frame.
- Adds guards against implausibly fast repetitions (`>=400 ms` from detected rep start) and immediate repeat counting (300 ms cooldown). These are *experimental* limits, not physiotherapy standards; calibrate with real volunteers before claiming accuracy.
- The serial Arduino packet is unchanged: `F,CURL,GOOD,OK,3\n` or `F,PUSHDOWN,BAD,LEAN,2\n` (and UNKNOWN). The existing OLED firmware is compatible; no Arduino reflash is needed for this patch.

## Apply on your current Git branch

1. Before any changes, confirm `git status` and commit or back up personal edits. The ZIP overwrites its listed files, not the whole repository.
2. Put `AUTOMOTION_DARK_CURL_PUSHDOWN_PATCH.zip` into the **existing** `auto-motion-tuesday` project folder (the folder with `main.py`). Do **not** drag a whole extracted directory into VS Code.
3. From the VS Code terminal in that folder:

   ```bash
   unzip -o AUTOMOTION_DARK_CURL_PUSHDOWN_PATCH.zip -d .
   .venv/bin/python -m pip install -r requirements.txt
   .venv/bin/python -m pytest -q
   ```

4. Double-click `START_AUTO_MOTION.command` (your existing camera 1 launch setting is preserved because the launcher is not included in this patch). If needed, launch manually:

   ```bash
   .venv/bin/python main.py --camera 1
   ```

5. Choose bicep curl or tricep pushdown, then LEFT/RIGHT. Position the camera around shoulder height, perpendicular to the bending plane, with shoulder/elbow/wrist/hip all visible. Click **Calibrate** while at the exercise's starting position and hold still ~1.5 s. Use no weight for your first tracking checks.

## How to evaluate real-world performance (not yet verified)

Perform five or more separate controlled trials for each scenario, with different body sizes, lighting and camera distances:

| Test | Movement | Expected behavior |
|---|---|---|
| C1 | Correct curl: arm mostly straight → bent → straight | One rep only after full sequence; no warning |
| C2 | Partial curl and return | Incomplete range warning; don't count a complete rep |
| C3 | Lean torso during curl for >400 ms | BAD / LEAN |
| C4 | Swing upper arm forward while curling | BAD / ARM |
| P1 | Correct pushdown: bent → extended → bent | One rep after full sequence |
| P2 | Partial pushdown and return | ROM warning; no full rep |
| P3 | Lean torso and rock back and forth | Sustained LEAN warning |
| P4 | Swing shoulder/upper arm while pressing | Sustained ARM warning |
| T1 | Block wrist/shoulder or step partly out of view | UNKNOWN with an actionable instruction |
| T2 | Hide the wrist for <0.5 s during an otherwise good rep | UNKNOWN while occluded; can resume without inventing a rep |
| T3 | Hide tracked joints for >0.5 s | UNKNOWN; restart from exercise home position |
| T4 | Rapid threshold oscillation / camera jitters | No double-counted rep |
| T5 | BAD on the last frame of a complete rep | Count as a flagged rep, not clean rep |
| A1 | Connect Arduino and switch modes | OLED displays mode, status, issue and rep count; disconnect shows camera-only |

Record **expected status, observed status, false warnings, missed warnings, rep count errors, and exact camera position**. Use at least 5 trials per failure/success case, ideally different people. Avoid publishing accuracy claims until you have an actual labeled dataset of trials.

## Scope / accuracy caveats

- Single camera with **2D** geometry cannot prove proper grip, load selection, shoulder rotation, joint safety, depth in 3D, or shoulder-blade movement. It should **not** claim to detect all mistakes in curls or pushdowns.
- For pushdowns, elbow extension measurement is most reliable with the arm moving roughly in the camera's image plane. Camera orientation and clothing/occlusion matter.
- GOOD = no programmed violation detected with sufficient tracked evidence. It does **not** prove the exercise is perfectly safe. UNKNOWN is expected when joints are hidden or there is no calibration.
- The application keeps all camera footage in memory and does **not** save or upload video.
- The current synthetic tests validate state transitions and UI behavior but cannot validate real-world pose estimation.

## Sources consulted (ideas only; code was not copied)

- Google, [MediaPipe Pose Landmarker](https://developers.google.com/edge/mediapipe/solutions/vision/pose_landmarker): normalized landmarks, visibility/presence confidence, live tracking behavior, valid outputs.
- [Pose-Estimation-with-Mediapipe](https://github.com/adsha27/Pose-Estimation-with-Mediapipe): dual thresholds/hysteresis to reject oscillation-based duplicate reps.
- [Exercise-Form-Correction](https://github.com/Meghul/Exercise-Form-Correction): user-facing rep counting and geometry-driven form warnings.
- [Metro Nova / Monotype](https://www.monotype.com/fonts/metro-nova): font licensing; only use it if properly licensed and installed.
