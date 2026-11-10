# Manbir — AUTO-MOTION Arduino R4 Screen + USB Serial

**Follow this guide step by step.** You own the **only Arduino portion**. Your UNO R4 Minima is NOT running AI, not deciding whether form is good, and not counting repetitions. Python on the Windows laptop sends a single status; the UNO R4 displays it on the available OLED.

**Your files:** `arduino/auto_motion_display/auto_motion_display.ino`, `arduino/i2c_scanner.ino`, `src/serial_link.py`, `scripts/send_demo.py`, and hardware notes in `docs/hardware_notes.md`.

## Tuesday's screen requirements

The status changes between:

- `GOOD` — no major torso lean detected by the limited Python rule (green on laptop video).
- `BAD` — sustained large lean detected (red on laptop video).
- `CANNOT ASSESS` — not calibrated, joints missing, wrist below shoulder, or no USB data (gray on laptop video).

A common SSD1306/SH1106 OLED is **monochrome**: it cannot physically display green, red and gray pixels. The Arduino screen will display the **words**. Do NOT spend time wiring external LEDs for Tuesday unless screen testing is finished; LEDs aren't required by the updated scope.

## Schedule

| When | Milestone | Approx. time |
|---|---|---:|
| **Sunday Nov 8 evening** | Clone repo; confirm board and OLED model; upload screen sketch | 2–3 hours |
| **Monday Nov 9 morning** | Fake-data serial sender cycles three states | 1–2 hours |
| **Monday Nov 9 afternoon** | Connect Rivan's live Python app; test connection loss | 1–2 hours |
| **Monday Nov 9 by 9 PM** | Firmware/test notes committed, working cable and board packed | 30 min |
| **Tuesday Nov 10** | Plug in and verify all three statuses | 20–30 min |

### M1. Clone the repo and establish a shared code environment (20–30 min)

1. Accept Rivan's invite to the private GitHub repo.
2. Install [Git](https://git-scm.com/downloads), [VS Code](https://code.visualstudio.com/), and [Python 3.11](https://www.python.org/downloads/) if needed.
3. In VS Code Terminal, clone it (replace `OWNER_USERNAME`):

**Windows PowerShell:**

```powershell
git clone https://github.com/OWNER_USERNAME/auto-motion-tuesday.git
cd auto-motion-tuesday
git switch -c manbir/arduino-display
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pytest -q
```

**Apple Silicon Mac Terminal:**

```bash
git clone https://github.com/OWNER_USERNAME/auto-motion-tuesday.git
cd auto-motion-tuesday
git switch -c manbir/arduino-display
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pytest -q
```

**Intel Mac:** MediaPipe may lack a native Python wheel. You don't need it to test USB communication. In a Python 3.11 virtual environment install `pyserial pytest` only; then run the serial sender with that interpreter. The full demo is on Windows.

**Check:** Basic tests pass. Learn that `src/serial_link.py` sends `S,GOOD\n`, `S,BAD\n`, `S,UNKNOWN\n` at 115200 baud; it never sends joint coordinates or video to the Arduino.

### M2. Identify the exact Arduino and OLED hardware (30–45 min)

**Required:** Arduino **UNO R4 Minima**, data-capable USB-C cable, the existing screen or shield. No extra camera board, ESP32, Raspberry Pi or wireless link.

1. Install [Arduino IDE 2](https://www.arduino.cc/en/software) on the computer that will upload the sketch.
2. Connect the R4 Minima with the USB-C **data cable**.
3. In Arduino IDE **Tools → Board → Boards Manager**, search for **Arduino UNO R4 Boards**, install the package.
4. Select **Arduino UNO R4 Minima** and its detected serial/COM port under **Tools**.
5. Open **File → Examples → 01.Basics → Blink** and click **Upload**. Confirm the built-in LED blinks. If it fails, try a data cable and board/port selection before debugging custom code.
6. Inspect the screen: is it an **I2C 128×64 SSD1306**, an **SH1106**, or a different screen/shield? Check writing on the PCB or product documentation. The current kit cannot know this hardware detail in advance.
7. If the screen uses I2C wires: **VCC**, **GND**, **SDA**, **SCL**, connect according to its rated voltage and pinout. UNO R4 default I2C is **SDA/A4** and **SCL/A5**; if the shield is prewired, do not add duplicate wiring.
8. The R4 has **5 V logic**. Some small displays require 3.3 V or level shifting; verify the module's electrical ratings before connecting its power/I2C lines.

**Screen diagnostic if needed:** In Arduino IDE, create a new sketch and paste the contents of `arduino/i2c_scanner.ino`; upload, open **Serial Monitor at 115200 baud**. Many SSD1306/SH1106 modules respond at **0x3C** (or **0x3D**). **Finding an I2C address does NOT identify the screen controller.** If nothing responds, check actual wiring, display power, or whether it's even an I2C device.

**Why:** The screen model is the one significant hardware unknown. Avoid inventing a controller/library that may not match the kit's display.

### M3. Install the OLED library and upload display firmware (30–60 min)

1. Arduino IDE **Sketch → Include Library → Manage Libraries**; search **U8g2**, install the library by olikraus.
2. In Arduino IDE use **File → Open**, choose `arduino/auto_motion_display/auto_motion_display.ino`. Ensure the sketch is inside its `auto_motion_display` folder (Arduino IDE may request moving it into that folder if moved elsewhere).
3. Read the first lines of the sketch. Default:

```cpp
#define OLED_DRIVER 1   // SSD1306 128x64 I2C
#define OLED_ADDR 0x3C
```

4. If hardware is **SH1106 128×64**, change `OLED_DRIVER` to `2`. If address scanner says **0x3D**, change address to `0x3D`. If the screen is neither controller or is 128×32 or SPI, **don't guess**: identify it and adapt the U8g2 constructor to the exact module before the demo.
5. Click **Verify**, then **Upload**. The display should initially show `AUTO-MOTION / SHOULDER` and `CANNOT ASSESS` (because no valid Python data has arrived).
6. Restart the Arduino. Verify the screen still shows `CANNOT ASSESS`.

**If OLED black:** Verify power & ground and correct voltage, use scanner, confirm screen size/controller, test SSD1306 vs SH1106 only if those are plausible. Some prewired shields are not I2C or use non-U8g2 controllers; consult the shield pinout before more changes.

**Why:** Screen functionality must be tested separately from AI so troubleshooting doesn't confuse hardware and model problems.

### M4. Test USB packets WITHOUT any camera (30–45 min)

This is the most important independent test. It allows the Arduino and screen to work without Rivan's AI code.

1. Connect the board to your computer and close the **Arduino Serial Monitor** (only one application should own the USB port).
2. Find the port:

**Windows:**

```powershell
.venv\Scripts\python.exe -m serial.tools.list_ports
```

**Mac:**

```bash
.venv/bin/python -m serial.tools.list_ports
```

3. Use the actual port printed, such as `COM3` on Windows or `/dev/cu.usbmodemNNNN` on a Mac. The next command shows only an example; replace the port name:

**Windows:**

```powershell
.venv\Scripts\python.exe scripts\send_demo.py --port COM3
```

**Mac:**

```bash
.venv/bin/python scripts/send_demo.py --port /dev/cu.usbmodemNNNN
```

4. The program will transmit `UNKNOWN → GOOD → BAD → GOOD → UNKNOWN`, each held for approximately 3 seconds.
5. Confirm the OLED changes accordingly. **If there's no update**, check the COM port, Arduino code uploaded, baud rate **115200**, and that Serial Monitor is closed.
6. After the sender finishes, wait 1–2 seconds: the OLED should stay/show `CANNOT ASSESS` because the firmware has a 1200 ms data timeout.
7. Repeat once. Log exact board type, screen controller, I2C address, port and result in `docs/hardware_notes.md`.

**What you're learning:** `pyserial` transports short ASCII text; the Arduino line parser recognizes only `S,GOOD`, `S,BAD`, `S,UNKNOWN`. Invalid packets are ignored, avoiding accidental statuses.

### M5. Understand the firmware before making changes (20 min)

Read `auto_motion_display.ino`:

- `Serial.begin(115200)` opens USB serial.
- `Wire.begin()` starts I2C for the OLED.
- `readSerial()` reads characters until newline `\n`, without blocking the main loop.
- `parsePacket()` recognizes only the three status values; unrecognized messages do not update the display.
- `lastStatusMs` records the time of each valid status message.
- If no valid packet arrives for 1200 ms, firmware sets `CANNOT ASSESS`.
- `drawStatus()` updates the OLED; it does **not** compute form or count repetitions.

**Do not add:** pose estimation, joint calculations, rep counting, external LED control, or complex menus before Tuesday.

### M6. Integrate the live Python camera and Arduino (45–90 min, Monday)

1. Ensure your standalone fake-status test passes first. Give the working board and cable to Rivan at the agreed integration time.
2. On the Windows demo laptop, connect the UNO R4 and run:

```powershell
.venv\Scripts\python.exe -m serial.tools.list_ports
```

3. Close the Arduino IDE Serial Monitor, then run (substitute the real COM port):

```powershell
.venv\Scripts\python.exe main.py --side left --port COM3
```

4. Before calibration: screen `CANNOT ASSESS`.
5. Press **C** while participant stands upright with arm down; wait 2 s. Raise selected wrist overhead: `GOOD`.
6. Hold an observable large torso lean for 700 ms or more after threshold crossing: `BAD`.
7. Return upright: `GOOD`. Lower arm/hide wrist: `CANNOT ASSESS`.
8. **Failure test:** disconnect USB while the system is running. The display will turn off if it has no separate power; if it remains powered but serial stops, it must show `CANNOT ASSESS` after 1200 ms. After reconnecting, restart the Python program with the newly detected COM port. Don't claim the screen can display anything when physically unpowered.

**If the live app runs without a port:** that is camera-only mode, not a serial failure. The app requires `--port PORT_NAME` to talk to the board.

### M7. Git handoff, pack, and Tuesday setup (20–30 min)

On your `manbir/arduino-display` branch:

```bash
git status
git add arduino/ src/serial_link.py scripts/send_demo.py docs/hardware_notes.md
git commit -m "Verify Arduino OLED status display and USB communication"
git push -u origin manbir/arduino-display
```

Open a GitHub PR into `main`; ask Rivan or Karthik to review and merge. Don't overwrite their other Python files. If you need to fix firmware after merging, create another small branch and PR rather than editing `main` directly.

Pack **the actual tested USB data cable, Arduino, OLED shield, and laptop charger**. Keep the verified Arduino sketch available offline. For Tuesday, the sequence is: plug board → run Python app with `--port` → camera preview → calibration → GREEN/GOOD → RED/BAD → GRAY/CANNOT ASSESS.

## Your completion checklist

- [ ] Arduino UNO R4 Minima board package installed and Blink works.
- [ ] OLED controller/address and voltage checked, hardware notes made.
- [ ] U8g2 installed, screen shows initial `CANNOT ASSESS`.
- [ ] `send_demo.py` cycles all three display words.
- [ ] Screen times out correctly if serial messages stop while still powered.
- [ ] Live Python status controls the screen.
- [ ] Firmware and notes committed and PR merged before Monday code freeze.
- [ ] Tested cable/board/screen available for Tuesday.

## External references

[Arduino UNO R4 Minima](https://docs.arduino.cc/hardware/uno-r4-minima/) · [R4 pinout PDF](https://docs.arduino.cc/5e218c7ed3622cbd09ab25357c345b84/ABX00080-full-pinout.pdf) · [U8g2 library](https://github.com/olikraus/u8g2) · [Arduino IDE](https://www.arduino.cc/en/software) · [pySerial short guide](https://pyserial.readthedocs.io/en/latest/shortintro.html)
