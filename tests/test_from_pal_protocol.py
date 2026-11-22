"""Send Python packets through the FROM-PAL loop with simulated hardware."""
import shutil
import subprocess

import pytest

from serial_link import feedback_packet, packet


def test_from_pal_display_modes_and_serial_connection(tmp_path, pytestconfig):
    compiler = shutil.which("c++")
    if compiler is None:
        pytest.skip("C++ compiler required for the firmware loop test")

    (tmp_path / "Arduino.h").write_text("""
#pragma once
#include <algorithm>
#include <stdint.h>
#include <stdlib.h>
#include <string>
using std::max;
using std::min;
const int LOW = 0, HIGH = 1, INPUT_PULLUP = 2, OUTPUT = 3, INPUT = 4;

struct TestSerial {
    std::string input;
    void begin(unsigned long) {}
    bool available() { return !input.empty(); }
    int read() {
        char ch = input.front();
        input.erase(0, 1);
        return ch;
    }
    template <class T> void print(T) {}
    template <class T> void println(T) {}
};
extern TestSerial Serial;

unsigned long millis();
int digitalRead(int pin);
unsigned long pulseIn(int pin, int level, unsigned long timeout);
inline void pinMode(int, int) {}
inline void digitalWrite(int, int) {}
inline void delayMicroseconds(unsigned int) {}
""")
    (tmp_path / "Wire.h").write_text("""
#pragma once
struct TestWire {
    void begin() {}
    void beginTransmission(int) {}
    int endTransmission() { return 0; }
};
extern TestWire Wire;
""")
    (tmp_path / "Adafruit_GFX.h").touch()
    (tmp_path / "Adafruit_SSD1306.h").write_text("""
#pragma once
#include <sstream>
const int SSD1306_SWITCHCAPVCC = 0, SSD1306_WHITE = 1;

struct Adafruit_SSD1306 {
    std::ostringstream buffer;
    std::string visible;

    Adafruit_SSD1306(int, int, void*, int) {}
    bool begin(int, int, bool, bool) { return true; }
    void setTextColor(int) {}
    void setTextSize(int) {}
    void setCursor(int, int) {}
    int width() { return 128; }
    template <class T> void print(T value) { buffer << value; }
    void clearDisplay() { buffer.str(""); }
    void display() { visible = buffer.str(); }
};
""")
    source = tmp_path / "firmware_test.cpp"
    source.write_text("""
#include <cassert>
#include <iostream>
#include "Arduino.h"
#include "Wire.h"

TestSerial Serial;
TestWire Wire;
unsigned long now = 0;
int buttonLevel = HIGH;
int distanceSamples = 0;
unsigned long millis() { return now; }
int digitalRead(int) { return buttonLevel; }
unsigned long pulseIn(int, int, unsigned long) {
    distanceSamples++;
    return 2000;
}

// Arduino normally generates these declarations when compiling the sketch.
int getDistance();
void resetTracking();
void updateDisplay();
void trackDistance();
#include "FROM-PAL.ino"

bool shows(const char *text) {
    return display.visible.find(text) != std::string::npos;
}

void feedLine() {
    assert(std::getline(std::cin, Serial.input));
    Serial.input += '\\n';
    loop();
}

void pressButton() {
    buttonLevel = LOW;
    loop();
    now += DEBOUNCE_MS + 1;
    loop();
    now += DEBOUNCE_MS + 1;
    loop();  // A held button advances once.
    buttonLevel = HIGH;
    loop();
    now += DEBOUNCE_MS + 1;
    loop();
}

int main() {
    setup();
    assert(shows(">Chest: "));
    pressButton();
    assert(shows("DESKTOP") && shows("NO CONNECTION"));
    pressButton();
    assert(shows(">Shoulder: "));

    feedLine();  // The initial valid packet selects Desktop.
    assert(motionConnected && shows("BICEP CURL") && shows("GOOD") && shows("Reps: 3"));
    feedLine();
    assert(shows("Reps: 4"));
    feedLine();
    assert(shows("TRICEP PUSHDOWN") && shows("GOOD") && shows("Reps: 4"));
    int samplesBefore = distanceSamples;
    now += SAMPLE_INTERVAL_MS;
    loop();
    assert(distanceSamples == samplesBefore);

    pressButton();
    assert(shows(">Shoulder: "));
    registerRep(startingDistance + 10);
    assert(repCountShoulder == 1 && repCountChest == 0);
    feedLine();  // Live status updates stay off the standalone screen.
    assert(motionStatus == FORM_BAD && shows(">Shoulder: ") && !shows("BAD"));
    pressButton();
    assert(shows(">Chest: "));
    registerRep(startingDistance + 10);
    assert(repCountShoulder == 1 && repCountChest == 1);
    feedLine();
    assert(motionStatus == CANNOT_ASSESS && shows(">Chest: ") && !shows("UNKNOWN"));
    pressButton();
    assert(shows("TRICEP PUSHDOWN") && shows("UNKNOWN") && shows("Reps: 9999"));

    const unsigned long lastValid = motionLastStatusMs;
    now = lastValid + MOTION_TIMEOUT_MS - 1;
    feedLine();  // Too many rep digits.
    feedLine();  // Bad issue.
    feedLine();  // Overflow must discard the entire line.
    assert(motionLastStatusMs == lastValid && motionConnected && shows("Reps: 9999"));
    now++;
    loop();
    assert(!motionConnected && shows("NO CONNECTION") && !shows("UNKNOWN") && !shows("Reps:"));
    pressButton();
    assert(shows(">Shoulder: "));

    feedLine();  // Reconnection selects Desktop. Legacy status remains supported.
    assert(motionConnected && shows("DESKTOP") && shows("BAD") && !shows("Reps:"));
}
""")
    executable = tmp_path / "firmware_test"
    subprocess.run(
        [compiler, "-std=c++11", "-I", str(tmp_path), "-I",
         str(pytestconfig.rootpath / "FROM-PAL"), str(source), "-o", str(executable)],
        check=True,
    )
    payload = b"".join([
        feedback_packet("curl", "GOOD", "OK", 3),
        feedback_packet("curl", "GOOD", "OK", 4),
        feedback_packet("pushdown", "GOOD", "OK", 4),
        feedback_packet("pushdown", "BAD", "LEAN", 17).replace(b"\n", b"\r\n"),
        feedback_packet("pushdown", "UNKNOWN", "TRACK", 9999),
        b"F,CURL,GOOD,OK,10000\n",
        b"F,CURL,GOOD,,6\n",
        b"X" * 30 + packet("GOOD"),
        packet("BAD"),
    ])
    subprocess.run([str(executable)], input=payload, check=True)
