# AUTO-MOTION and FROM-PAL

The root app tracks bicep curls and tricep pushdowns with a webcam. It sends the
selected exercise, form status, issue code, and rep count to the FROM-PAL OLED
over USB at 115200 baud.

## Launch the arm app

From the repository root with Python 3.11:

```sh
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
mkdir -p models
curl -fL https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task -o models/pose_landmarker_lite.task
.venv/bin/python main.py --exercise curl --side right --camera 0
```

Skip setup for an existing environment and model. Use `--exercise pushdown` to
start in pushdown mode. In the app, **1** selects curl, **2** selects pushdown,
**C** calibrates, **R** selects the right arm, and **Q** quits. Use **Reset reps**
to clear the count. Calibrate after changing
exercises or arms. The separate `Auto-motion/main.py` is the teammate camera
demo. Launch the root `main.py` for curl and pushdown.

The app auto-selects a single recognized Arduino. If detection is ambiguous or
the board uses an unrecognized USB adapter, run
`.venv/bin/python -m serial.tools.list_ports -v` and pass the board's actual
device with `--port`. Close Arduino Serial Monitor before launching the app.
Use the in-app Arduino button to reconnect after plugging the board back in.

## Upload FROM-PAL

1. Connect the board via a USB data cable. For the UNO R4 Minima, connect the
   OLED's SDA to SDA/A4 and SCL to SCL/A5, with common GND. Use the power supply
   and I2C logic levels required by the OLED module. The sketch expects a
   128×64 I2C SSD1306 at address `0x3C` or `0x3D`.
2. In Arduino IDE, open `FROM-PAL/FROM-PAL.ino`. Install **Adafruit SSD1306** and
   **Adafruit GFX Library**, including their dependencies. Select
   **Arduino UNO R4 Minima** if that is your board, select its USB port, and click
   **Upload**.
3. Start the root app. The first valid feedback packet selects Desktop mode and
   shows the exercise, GOOD/BAD/UNKNOWN, and the app's rep count.
4. Press the board's button to cycle **Shoulder → Chest → Desktop → Shoulder**.
   The `>` marks the active standalone mode. Incoming packets keep Desktop
   feedback current while you use Shoulder or Chest.
5. After 1.2 seconds without valid packets, Desktop shows **NO CONNECTION**.
   You can still cycle modes, including entering Desktop while offline. The
   first valid packet after a timeout selects Desktop again.

To check the OLED separately, quit the app and open Serial Monitor at 115200
with newline enabled. Send `F,CURL,GOOD,OK,3` and check for **BICEP CURL**, **GOOD**,
and **Reps: 3** before the timeout. Close Serial Monitor afterward.

## Roles

- Karthik converts camera observations into form feedback.
- Manbir operates the camera and measures exercise movement.
- Rivan integrates form feedback with the OLED.
- Graham built FROM-PAL.
