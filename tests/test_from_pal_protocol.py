"""Feed the live Python encoder into the production firmware parser."""
import shutil
import subprocess

import pytest

from src.serial_link import feedback_packet, packet


def test_from_pal_arm_feedback_and_legacy_fallback(tmp_path, pytestconfig):
    compiler = shutil.which("c++")
    if compiler is None:
        pytest.skip("C++ compiler required for firmware parser test")

    (tmp_path / "Arduino.h").write_text("""
#include <stdint.h>
#include <string>
struct TestSerial {
    std::string input;
    bool available() { return !input.empty(); }
    int read() {
        char ch = input.front();
        input.erase(0, 1);
        return ch;
    }
};
extern TestSerial Serial;
unsigned long millis();
""")
    (tmp_path / "Adafruit_SSD1306.h").write_text("""
struct Adafruit_SSD1306 {
    void setTextSize(int) {}
    void setCursor(int, int) {}
    int width() { return 128; }
    template <class T> void print(T) {}
};
""")
    source = tmp_path / "parser_test.cpp"
    source.write_text("""
#include <cassert>
#include <iostream>
#include "auto_motion_display.h"

TestSerial Serial;
unsigned long now = 1;
unsigned long millis() { return now; }

bool feedLine() {
    std::getline(std::cin, Serial.input);
    Serial.input += '\\n';
    return motionUpdate();
}

int main() {
    assert(feedLine());  // The first arm packet activates the arm display state.
    assert(motionExercise == CURL && motionStatus == FORM_GOOD && motionReps == 3);
    assert(feedLine());
    assert(motionExercise == CURL && motionStatus == FORM_GOOD && motionReps == 4);
    assert(feedLine());
    assert(motionExercise == PUSHDOWN && motionStatus == FORM_GOOD && motionReps == 4);
    assert(feedLine());
    assert(motionExercise == PUSHDOWN && motionStatus == FORM_BAD && motionReps == 17);
    assert(feedLine());
    assert(motionExercise == PUSHDOWN && motionStatus == CANNOT_ASSESS && motionReps == 9999);
    now += 100;
    assert(!feedLine()); // Too many rep digits.
    assert(!feedLine()); // Bad issue.
    assert(!feedLine()); // Overflow must discard the entire line.
    assert(motionLastStatusMs == 1);
    now = 1202;
    assert(motionUpdate());
    assert(motionExercise == NO_ARM_EXERCISE && motionStatus == CANNOT_ASSESS);
    assert(feedLine());  // Legacy status still works.
    assert(motionExercise == NO_ARM_EXERCISE && motionStatus == FORM_BAD);
}
""")
    executable = tmp_path / "parser_test"
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
