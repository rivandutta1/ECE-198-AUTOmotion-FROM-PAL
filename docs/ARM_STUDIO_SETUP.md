# AUTO-MOTION Arm Studio — Curl + Tricep Pushdown

**New branch:** `karthik/arm-exercises` (create from original `karthik/form-rules` branch). This kit deliberately replaces the old shoulder-press *demo entry point* `main.py` but leaves `src/geometry.py`, `src/form_rules.py`, and all pre-existing tests untouched. Do **not** push directly to `main`.

## Quick start: MacBook webcam

From the **original** project directory (where `main.py` lives):

```bash
git status --short
git switch -c karthik/arm-exercises
# Copy patch ZIP into this directory without double-clicking it, then:
unzip -o AUTO_MOTION_ARM_STUDIO_PATCH.zip -d .
.venv/bin/python -m pytest -q
.venv/bin/python main.py --exercise curl --side right --camera 0
```

If your Mac defaults to the iPhone Continuity Camera, try `--camera 1` or disable Continuity Camera on the iPhone. This only selects camera 0; the Mac determines which camera is #0. Do not run `git reset --hard` after applying the patch unless you intend to discard it.

If your model is missing, download the official Pose Landmarker Lite model:

```bash
curl -fL -o models/pose_landmarker_lite.task \
  'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task'
```

The `models/` folder is *not* included in the patch and should be preserved.

**Windows PowerShell**: run `.venv\Scripts\python.exe` instead of `.venv/bin/python`; use `py -3.11 -m pip install -r requirements.txt` if creating a new environment.

## Modes / keyboard

| Key / CLI | Action |
|---|---|
| `--exercise curl` or `1` | Right-arm bicep curl |
| `--exercise pushdown` or `2` | Right-arm cable tricep pushdown |
| `C` | Calibrate the current exercise (about 1.5 seconds) |
| `R` | Reset rep counters; keep calibration |
| `Q` or `Esc` | Quit and release webcam/serial |
| `--side right` | Track MediaPipe RIGHT shoulder/elbow/wrist/hip (default). Keep side-on to webcam. |
| `--camera 0` | First available webcam; select another index if needed |
| `--port /dev/cu.usbmodem...` | Send live results to connected Arduino OLED |

Keyboard shortcuts work when the **OpenCV AUTO-MOTION window** has keyboard focus, not VS Code. Click the AUTO-MOTION window before pressing keys.

## Bicep curl test (no weights to begin)

1. Stand **sideways** with right shoulder, elbow, wrist, **and hip** all in frame. Camera ~chest height; step back until your joints are clearly tracked. Good lighting, fixed camera.
2. Begin with your **right arm nearly straight and relaxed downward** (elbow angle >145°). Click the AUTO-MOTION window, press `1`, then `C`.
3. Remain still for 1.5–2 seconds. Screen should say `CALIBRATED` then `READY`.
4. Bend elbow, hand toward shoulder; return until nearly straight. In demo, a curl rep uses **angle ≤95° at top and ≥150° at bottom**.
5. Watch the joint skeleton, elbow angle, rep count, movement progress and form message. If the top never reaches the demo threshold, returning down should produce a ROM warning. Lean the torso only gently to test sustained lean warning; avoid unsafe movements.

## Tricep pushdown test (no weights to begin)

1. Keep the same stable **side view of your RIGHT arm**, wrist/elbow/hip visible. Face the direction a cable machine would face; keep your upper arm near your torso.
2. Press `2` to switch modes. **Bend your right elbow** to an angle between ~65° and 135° to imitate a pushdown starting position (forearm roughly in front of you). Press `C`, hold still about 1.5–2 seconds.
3. Extend the elbow **downward** like a cable pushdown, then return to the bent starting position. The experimental rep thresholds are **≥160° extended and ≤115° returned**.
4. Watch for reps, elbow extension, torso swaying, upper-arm drift, and incomplete extension warnings.

**Important:** We cannot determine actual cable tension, weights, elbow joint health, grip, or true 3D joint orientation from a single laptop camera. Don't use a GOOD result as proof that the lift is safe or perfect.

## Arduino UNO R4 Minima + 128×64 I2C OLED

1. Connect your OLED properly (for UNO R4 Minima, check the board's SDA/SCL pins, common GND, display voltage specifications). Do not guess voltage/pin wiring; check the module's datasheet.
2. Open `arduino/auto_motion_display/auto_motion_display.ino` in **Arduino IDE**. Install the **U8g2** library. Select **Arduino UNO R4 Minima** and the correct USB port, then **Upload**. If SH1106, change `OLED_DRIVER 1` to `2`. If address isn't `0x3C`, use `arduino/i2c_scanner.ino` to identify the OLED before setting `OLED_ADDR`.
3. **Close Arduino IDE Serial Monitor** before running Python (one application at a time can own the port).
4. Discover the port:

```bash
.venv/bin/python -m serial.tools.list_ports
```

5. Launch with the **actual** port (example only, yours will differ):

```bash
.venv/bin/python main.py --exercise curl --side right --camera 0 --port /dev/cu.usbmodem101
```

The OLED shows **exercise / GOOD-BAD-CANNOT ASSESS / main warning / rep count**. It receives the same status as the webcam at ~5 updates/s. Protocol at 115200 baud: `F,CURL,GOOD,OK,2\n` or `F,PUSHDOWN,BAD,LEAN,4\n`. Legacy `S,GOOD\n` remains supported by the Arduino firmware. When no valid serial data arrives for 1.2s, the OLED falls back to CANNOT ASSESS.

## Detection architecture and trust

- `src/vision.py` (original): MediaPipe Pose Landmarker Lite. One person; **2D image landmarks** only.
- `src/arm_exercises.py` (new): validates right-side landmarks; computes pixel-corrected elbow angle, torso shift, and upper-arm drift relative to stable start pose. Smooths elbow angles over **3 frames**. Counts reps via start → target → return; partially completed movements produce a ROM warning. Sustained torso/upper-arm motion produces warnings after **400ms**.
- `src/arm_ui.py` (new): live preview with overlay and clearly labeled form status. No file or raw video is saved.
- `src/serial_link.py` + Arduino firmware (updated): robust protocol, validates fields, never sends GREEN when UNKNOWN, preserves original S packets.

**Prototype thresholds, not scientifically validated:** curl: elbow ≤95° / ≥150°; pushdown ≥160° / ≤115°; torso drift ~14°/12°; upper-arm drift ~24°/18°. User-to-user camera placement changes angles substantially. Screen labels GOOD means *no rule was triggered for this visible movement*, NOT clinically good form. The algorithm cannot reliably detect wrist/grip mechanics, scapular position, resistance, cable tension or all forms of cheating.

## Test checklist / troubleshooting

| Test | Expected |
|---|---|
| No pose / wrist outside image | UNKNOWN + prompts which joint to show |
| Before calibration | UNKNOWN and PRESS C |
| Move during calibration | UNKNOWN and retry prompt |
| Right curl through start/top/start | GOOD during movement, rep increments once |
| Right pushdown through bent/extended/bent | GOOD during movement, rep increments once |
| Incomplete curl or pushdown | BAD + PARTIAL RANGE on return |
| Sustained upper-arm drift | BAD + KEEP UPPER ARM STEADY |
| Sustained excessive torso change | BAD + STOP TORSO SWINGING |
| Camera occlusion mid-rep | UNKNOWN; no false rep when tracking returns |
| Press `2` to switch exercise | New exercise + recalibration required |
| Disconnect USB after connected | Python continues webcam-only on serial failure; OLED times out to CANNOT ASSESS |

After physical testing, **record observed output** in `docs/test_results.md` or a separate session log; do not claim a numerical accuracy percentage from synthetic unit tests. Adjust thresholds only when repeated camera evidence warrants it. Only after real camera and OLED tests, stage the relevant files, commit on `karthik/arm-exercises`, push, and open a pull request for Rivan and Manbir to review.

## Tracking reliability update (November 2026)

The original Arm Studio was unnecessarily strict on some cameras. This update:

- Accepts **visibility >= 0.45** and **presence >= 0.35** for each required joint (previously both needed >= 0.65). Missing/offscreen joints still return `UNKNOWN`; these numbers are pragmatic *prototype* settings, not validated confidence/accuracy cutoffs.
- Treats model attributes with no confidence score (`None`) as unspecified rather than crashing.
- Uses frame-relative distance checks instead of requiring a fixed number of pixels between joints.
- Allows the opposite hip as a **last-resort** 2D hip estimate when the selected-side hip is hidden. A sudden change in which hip is visible can shift the projected torso angle, so keep both hips in frame when possible.
- Retains rep state for a brief (<500 ms) tracking interruption. During *every* missing frame the webcam and Arduino still receive `UNKNOWN`, never a fabricated `GOOD`. After longer gaps, the rep is cancelled and you must return to the start position.
- Preserves calibration samples through momentary (<500 ms) failures, and ignores the most extreme ~10% of samples when checking calibration stability. It still refuses visibly moving calibration poses.
- Smooths the elbow, torso, and upper-arm angles with short, three-valid-frame median filters. This slightly delays responses in exchange for reducing sudden false jumps.
- Shows `READY / WAIT` in the camera UI when you are calibrated and waiting to exercise. The *underlying Arduino protocol remains* `UNKNOWN` while idle (the software is **not** assessing a lift then).
- Adds `--debug-tracking` diagnostics, printing status and a short human-readable reason when they change, without recording webcam images.

### Recommended trial

With your **right shoulder, elbow, wrist and hip visible**, stand with your *right side* facing the camera. Set the webcam roughly at chest height, keep the hand clear of your torso, and ensure that the full arm/hip remain in frame. Use good, even lighting and a fixed camera. If you cannot see the drawn elbow and wrist consistently, move farther away or rotate slightly to improve separation. These steps matter more than reducing confidence thresholds further.

```bash
.venv/bin/python main.py --exercise curl --side right --camera 0 --debug-tracking
# Or use:
.venv/bin/python main.py --exercise pushdown --side right --camera 0 --debug-tracking
```

Click the OpenCV window, press **C**, hold the required start position still, and wait to see `CALIBRATED`. When ready, perform three slow unloaded reps with the whole right arm in frame. Note which joint or status reason appears if tracking is lost. Compare the status, elbow angle, and rep counter to what you actually did, not only the synthetic test suite.

### Optional higher-capacity model

MediaPipe also publishes a `full` Pose Landmarker model. Download it from the model linked in Google's official Pose Landmarker documentation, or run:

```bash
mkdir -p models
curl -fL -o models/pose_landmarker_full.task 'https://huggingface.co/litert-community/MediaPipe-PoseLandmarker-Full/resolve/main/pose_landmarker_full.task'
.venv/bin/python main.py --exercise curl --side right --camera 0 --model full --debug-tracking
```

`--model lite` remains the default. The full model may improve landmark stability in some situations at the cost of processing speed, but **no benefit has been verified for your specific webcam**. Both are still single-camera 2D exercise screeners.

### What software tests can and cannot establish

Run `.venv/bin/python -m pytest -q`. These tests cover geometry, status handling, dropout recovery, calibration tolerance, serial packet correctness, and UI rendering. They **do not establish field accuracy, rep count accuracy, camera performance, or OLED hardware correctness**. Before claiming consistency, record at least five successful and five troublesome real-world trials of *each* exercise, with camera angle, lighting, measured elbow range, status, and rep count. Keep `UNKNOWN` when key joints remain unobservable.
