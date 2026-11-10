# AUTO-MOTION — Arduino Display Hardware Notes

## Development Status — November 10, 2026

**Assigned developer:** Rivan Dutta  
**Git branch:** `rivan/arduino-display`  
**Development computer:** Apple Silicon MacBook  
**Hardware availability:** Arduino and OLED currently unavailable

### 1. Completed Setup (M1)

- Created the shared private GitHub repository: `rivandutta1/auto-motion-tuesday`.
- Established the local repository and personal development branch.
- Installed and selected Python 3.11.18 through Homebrew.
- Created the Python virtual environment (`.venv`).
- Installed Python dependencies from `requirements.txt`.
- Ran the automated Python test suite: **11 tests passed**.

### 2. Arduino Development Environment (M2)

**Completed:**
- Installed Arduino IDE 2.3.10 on macOS.
- Installed Arduino UNO R4 Boards package version 1.6.0.
- Selected Arduino UNO R4 Minima as the target board.

**Not completed — awaiting hardware:**
- M2.2: Connect the Arduino using a data-capable USB-C cable.
- M2.4: Confirm the actual serial port.
- M2.5: Upload and test the Blink example.
- M2.6: Identify the OLED controller and resolution.
- M2.7: Connect or inspect the OLED wiring.
- M2.8: Verify the OLED voltage and I2C electrical compatibility before wiring.
- Optional: Run the I2C scanner if required to identify the display address.

**Hardware assumptions (unverified):**
- Microcontroller: Arduino UNO R4 Minima.
- Default OLED configuration: SSD1306, 128×64, I2C.
- Assumed I2C address: `0x3C`.
- Alternative supported controller: SH1106.

The actual display controller and address must be confirmed before hardware testing.

### 3. Arduino Display Firmware (M3)

**Completed:**
- Opened and reviewed `arduino/auto_motion_display/auto_motion_display.ino`.
- Added explanatory comments to improve understanding and maintainability.

**Verification still to confirm:**
- U8g2 library installation.
- Successful Arduino IDE compilation using Verify.

**Not completed — awaiting hardware:**
- M3.4: Confirm and adjust OLED driver/address if necessary.
- M3.5: Upload firmware and test the initial OLED output.
- M3.6: Restart the Arduino and confirm that the display initializes correctly.

### 4. Firmware Understanding (M5)

**Completed.**

Reviewed and understood the major components:

- Library imports and display-driver configuration.
- C++ classes, objects, constructors, and member functions.
- Status enumeration and global variables.
- Character buffers and pointer-based string handling.
- Serial input reading through `readSerial()`.
- Status interpretation through `parsePacket()`.
- OLED rendering through `drawStatus()`.
- Hardware initialization through `setup()`.
- Continuous operation through `loop()`.
- The 1,200 ms serial timeout and 150 ms display refresh interval.

**Serial message protocol:**
- `S,GOOD\n` → GOOD
- `S,BAD\n` → BAD
- `S,UNKNOWN\n` → CANNOT ASSESS

Baud rate: **115200**.

The Arduino is responsible only for receiving and displaying form statuses. Python performs the camera-based analysis.

### 5. USB Communication (M4)

**Status: Not tested — awaiting hardware.**

Remaining tasks:
- Detect the Arduino's USB serial port.
- Run `scripts/send_demo.py`.
- Verify that the OLED displays GOOD, BAD, and CANNOT ASSESS.
- Confirm that the display times out to CANNOT ASSESS when valid communication stops.
- Record the actual serial port and test results.

### 6. Live Camera Integration (M6)

**Status: Not tested — awaiting hardware and integration.**

Remaining tasks:
- Connect the Arduino to the computer running the Python camera application.
- Confirm that Python sends valid status messages.
- Verify the OLED responds to live camera results.
- Test disconnection and recovery behaviour.

### 7. GitHub Handoff (M7)

**In progress.**

- Arduino firmware comments have been committed locally.
- Confirm that commits are pushed to `rivan/arduino-display`.
- Add these hardware notes to the same branch.
- Complete hardware testing before claiming the prototype is verified.
- Request review and merge into `main` once the component is ready.

### 8. Current Stopping Point

Software setup and firmware study are complete.

The immediate next task is to confirm successful compilation of the Arduino sketch using Arduino IDE's **Verify** function.

After compilation and documentation are finished, physical Arduino and OLED access is required to complete the remaining assigned functionality.

**No physical Arduino/OLED functionality has been verified yet.**



