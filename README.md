# AUTO-MOTION Tuesday Starter Kit — ECE 198

**Target: Tuesday, November 10, 2026. Scope: ONE shoulder-press form warning, NO rep counter.**

The Windows laptop webcam runs MediaPipe Pose Landmarker in Python. A calibration stage records the user's upright side-view torso angle. If a large deviation (**18°** relative to baseline) is sustained for **700 ms** while the selected wrist is above the shoulder, Python outputs `BAD`. Otherwise while assessing the overhead movement it outputs `GOOD`. Uncalibrated, no pose, obscured joints, and arm-down positions output `UNKNOWN`.

This is an **experimental movement warning, not a clinical determination of correct form**. No video is recorded. Test unloaded movements with consenting team members. The proposed 18°/700 ms are unvalidated thresholds chosen to create an explainable demo; report and adjust them based on test results.

### Three documents to follow

1. [`docs/01_RIVAN_CAMERA_AND_GIT.md`](docs/01_RIVAN_CAMERA_AND_GIT.md) — Rivan: shared repo, Windows Python, model, live webcam, integration and demo.
2. [`docs/02_KARTHIK_FORM_LOGIC_AND_TESTING.md`](docs/02_KARTHIK_FORM_LOGIC_AND_TESTING.md) — Karthik: geometry, calibration, three-state form logic, tests and threshold validation.
3. [`docs/03_MANBIR_ARDUINO_AND_SERIAL.md`](docs/03_MANBIR_ARDUINO_AND_SERIAL.md) — Manbir: UNO R4 Minima + OLED, serial data, failure display and hardware tests.

### Shared program contract

- Python: 3.11.x, VS Code, `python -m pip install -r requirements.txt`.
- Model: `python scripts/download_model.py` (Google model; not included).
- Video: `python main.py --side left` (no Arduino); `python main.py --side left --port COM3` for Arduino on Windows (replace `COM3` with your port).
- Keyboard: **C = calibrate** while upright with arm down (stand still for 2 seconds); **Q = quit**.
- Python status: `GOOD` (large torso lean not detected), `BAD` (sustained large torso lean), `UNKNOWN` (cannot assess/arm down/not calibrated).
- USB serial: `115200` baud; ASCII `S,GOOD\n`, `S,BAD\n`, `S,UNKNOWN\n`, refreshed at about 5 messages/second.
- Arduino: text-only display; `GOOD`, `BAD`, `CANNOT ASSESS`. Standard monochrome OLEDs **cannot physically show green/red/gray**. The laptop video overlay uses the colors; no external LEDs are required for Tuesday.
- Hardware: ONE Arduino UNO R4 Minima; it only displays results. No rep counter, no serial data back to Python, no combined FROM-PAL app.
- Camera: single consenting person in side view, selected side (`--side left` or `--side right`) with shoulder, elbow, wrist and hip visible. Place laptop far enough back to keep the wrist in the image overhead. Good lighting; camera at torso height; no weights.

### Who works where?

Rivan: `main.py`, `src/vision.py`, `scripts/download_model.py` and integration.
Karthik: `src/geometry.py`, `src/form_rules.py`, `tests/test_geometry.py`, `tests/test_form_rules.py`, test results.
Manbir: `src/serial_link.py`, `scripts/send_demo.py`, `arduino/` and hardware test notes.

Use a **private** GitHub repository for this school prototype and avoid uploading identifying video. Keep original starter files intact on `main`; each person develops on their own Git branch and merges via GitHub pull requests. Do not upload video of patients or raw personal health data.

### Quick local checks (from project root)

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe scripts\download_model.py
.venv\Scripts\python.exe main.py --side left
```

macOS Apple Silicon with Python 3.11:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pytest -q
.venv/bin/python scripts/download_model.py
.venv/bin/python main.py --side left
```

Intel Macs may not have a current MediaPipe Tasks Python wheel. For mathematical module development on Intel Mac, use `python3 -m pip install pytest` and `python3 -m pytest -q` in a separate virtual environment; do not let the pose package prevent offline testing. Finish and demonstrate on the **Windows camera laptop**.

### Frequently encountered blockers

| Symptom | Check / action |
|---|---|
| `No module named mediapipe` | Confirm VS Code interpreter points to `.venv` and install `requirements.txt` using `.venv` Python. |
| Model file missing | Run `scripts/download_model.py` with internet access; model stays local after download. |
| Camera unavailable | Allow Windows camera permissions; close Teams/Zoom; try `--camera 1`. |
| Always `CANNOT ASSESS` | Press **C** with arm down and stand still; show hip/shoulder/wrist; use `--side right` if that side faces the camera. |
| Green even when leaning | Make sure wrist is overhead, stand sideways, hold a comfortable but visibly large lean for 700 ms; examine angle threshold with Karthik. |
| Bad when upright | Recalibrate with arm down, stable torso; check baseline before attempting an overhead press. |
| No COM port | Plug in a **data-capable** USB-C cable; install/select Arduino UNO R4 Minima board; run `python -m serial.tools.list_ports`. |
| Upload error or Python port error | Close Arduino Serial Monitor before Python connects; close Python before uploading firmware. |
| OLED remains black | This kit assumes a 128x64 **I2C SSD1306 at 0x3C**. Run `arduino/i2c_scanner.ino`, check screen supply and controller, try SH1106 selection; other shield types need a driver change. |
| USB unplugged | Firmware changes to `CANNOT ASSESS` after 1.2 seconds without valid data. Restart the Python program with the new port when reconnected. |

### Useful documentation

- [MediaPipe Pose Landmarker Python](https://developers.google.com/edge/mediapipe/solutions/vision/pose_landmarker/python)
- [MediaPipe Python supported platforms](https://developers.google.com/edge/mediapipe/solutions/setup_python)
- [Official Lite pose model](https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task)
- [OpenCV webcam tutorial](https://docs.opencv.org/4.x/dd/d43/tutorial_py_video_display.html)
- [UNO R4 Minima documentation](https://docs.arduino.cc/hardware/uno-r4-minima/)
- [U8g2 Arduino OLED library](https://github.com/olikraus/u8g2)
- [pySerial documentation](https://pyserial.readthedocs.io/en/latest/shortintro.html)

### Limitations of verification

The included Python mathematical/logic/serial-packet tests can be run without a camera (11 passing in the preparation environment). Actual MediaPipe inference, Windows webcam permissions, the physical UNO R4, and the exact OLED shield were **not** runnable in the file-building environment; the three guides contain first-on-device tests for these items. No separate AI reviewer agents were available in this conversation; implementation and integration/safety review were performed as two independent checklists instead.
