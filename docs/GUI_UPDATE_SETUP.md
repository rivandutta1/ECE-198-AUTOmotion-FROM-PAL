# AUTO-MOTION Fitness Assistant — clickable high-resolution interface

This update builds on the `karthik/arm-exercises` branch **after** the Arm Studio tracking-stability patch. It keeps the existing repo, tests, `.venv`, `models`, and Git history. Do **not** replace the whole repository.

## Install

1. In VS Code, work in your existing `auto-motion-tuesday` folder and confirm you are on the intended branch (`git branch --show-current`). **Back up any uncommitted changes** to the affected files first.
2. Move `AUTO_MOTION_EASY_UI_PATCH.zip` (the ZIP itself) into this project folder.
3. Run:

   ```bash
   unzip -o AUTO_MOTION_EASY_UI_PATCH.zip -d .
   chmod +x START_AUTO_MOTION.command
   .venv/bin/python -m pytest -q
   ```

4. On macOS, open the project folder in Finder and **double-click `START_AUTO_MOTION.command`** to launch. It opens a Terminal window automatically but no command typing is required. On the first launch macOS may require Finder right-click -> Open and camera permission. Do not disable system security settings. The `.venv` and `models/pose_landmarker_lite.task` must already exist.

   Developer alternative: `.venv/bin/python main.py`. Choose a different webcam if needed with `--camera 1`, or use the new **CHANGE CAMERA** button.

## All on-screen controls

- **BICEP CURL**, **TRICEP PUSHDOWN**, **SHOULDER PRESS**, **CHEST PRESS**: choose an exercise without restarting Python. Each change starts a *fresh calibration*.
- **RIGHT ARM**, **LEFT ARM**: choose which anatomical arm MediaPipe tracks, independent of the video mirror. Switching sides also starts a *fresh calibration*.
- **CALIBRATE**: captures your normal starting posture; hold still until ready. Curls start elbow nearly straight; pushdowns begin bent; shoulder press begins arm down, upright; chest press is **seated upright** with hands near the chest.
- **RESET REPS**: resets counts for curl and pushdown. The press modes **do not count reps**—they show N/A.
- **MIRROR ON/OFF**: flips the live preview like a mirror and flips the displayed joint skeleton to match. The underlying form angles and RIGHT/LEFT choices are unchanged.
- **CHANGE CAMERA**: searches camera indexes 0–3 for another working video source and switches to it; re-calibrate afterward. If none is found, the current camera remains selected.
- **CONNECT ARDUINO**: attempts to connect to the sole detected Arduino USB serial device. If no unique Arduino is found, it stays in camera-only mode rather than guessing the USB port.
- **EXIT**: closes the camera and serial port gracefully.

Optional keyboard shortcuts: 1/2/3/4 select exercises, L/R selects tracked side, C calibrates, M toggles mirroring, Q exits. Buttons are the primary interface.

## Sharper image and legible controls

- The program requests **1280x720** webcam frames (previously 640x480). Some cameras, Mac backends, and lighting situations supply a lower resolution anyway. The actual resolution and FPS are shown on the video. A larger display **does not itself increase camera detail**.
- The UI draws a **1600x900** native dashboard with large mouse buttons and guidance, letterboxes the video without stretching it, and overlays landmarks at positions adjusted for video mirroring. If it appears too big for your screen, resize the OpenCV window.
- For side-view form checks, ensure the selected shoulder, elbow, wrist, and hip are all visible. A mirror view doesn't change which anatomical arm is tracked.
- The software does not save video footage.

## Arduino OLED

1. Connect the Arduino UNO R4 Minima and OLED with correct board-specific wiring. Ask your teammate to verify the display controller (`SSD1306` vs `SH1106`), I2C address, supply voltage, and SDA/SCL pins.
2. In Arduino IDE, open `arduino/auto_motion_display/auto_motion_display.ino`, install the **U8g2** library, select the correct board/USB port, and **upload this updated sketch once**. Close Arduino IDE's Serial Monitor.
3. When the app starts, it tries to connect automatically if **exactly one recognized Arduino USB device** is found. Otherwise click **CONNECT ARDUINO**; for unusual USB serial adapters a developer may still need `--port /dev/cu.usbmodem...`.
4. Webcam and OLED both receive the selected exercise and the `GOOD` / `BAD` / `UNKNOWN` assessment. The OLED also receives the main issue and curl/pushdown rep count. Presses show `2D FORM` rather than inventing a rep count.
5. If the board disconnects, the app continues webcam-only and the OLED times out to `CANNOT ASSESS` instead of retaining a stale `GOOD` result.

## Scope and limitations

- **Curl / pushdown** use the existing Arm Studio calibration, elbow flexion/extension, upper-arm movement, torso drift, and rep counting. Form checks are unvalidated 2D heuristics.
- **Shoulder press / seated chest press** are from the *earlier experimental press monitor*. They assess observable projected cues only; no validated full-form classification and no rep counting. Shoulder press generally needs a side view; chest press needs a diagonal front/side view while **sitting upright**.
- One camera cannot prove a movement is clinically safe or that form is perfect. UNKNOWN remains UNKNOWN when key landmarks cannot be seen. The software does not check load, grip force, pain, or resistance.
- Automated unit tests check code paths but **cannot establish physical detection accuracy**. Do multiple trials with a real webcam for each mode and record inconsistent results before using with others.
