#ifndef AUTO_MOTION_DISPLAY_H
#define AUTO_MOTION_DISPLAY_H

#include <Arduino.h>
#include <string.h>
#include <Adafruit_SSD1306.h>

// Shares the OLED object defined in Project.ino
extern Adafruit_SSD1306 display;

// Python sends one line per update: S,GOOD / S,BAD / S,UNKNOWN
enum MotionStatus { CANNOT_ASSESS, FORM_GOOD, FORM_BAD };

static MotionStatus motionStatus = CANNOT_ASSESS;
static char motionBuffer[30];
static uint8_t motionCharsRead = 0;
static unsigned long motionLastStatusMs = 0;

const unsigned long MOTION_TIMEOUT_MS = 1200;   // no packet for this long -> CANNOT ASSESS

inline void motionParsePacket(const char *line) {
    if (strncmp(line, "S,", 2) != 0) return;
    const char *value = line + 2;

    if (strcmp(value, "GOOD") == 0) motionStatus = FORM_GOOD;
    else if (strcmp(value, "BAD") == 0) motionStatus = FORM_BAD;
    else if (strcmp(value, "UNKNOWN") == 0) motionStatus = CANNOT_ASSESS;
    else return;
    motionLastStatusMs = millis();
}

inline void motionReadSerial() {
    while (Serial.available() > 0) {
        char ch = (char) Serial.read();
        if (ch == '\r') continue;
        if (ch == '\n') {
            motionBuffer[motionCharsRead] = '\0';
            motionParsePacket(motionBuffer);
            motionCharsRead = 0;
        } else if (motionCharsRead < sizeof(motionBuffer) - 1) {
            motionBuffer[motionCharsRead++] = ch;
        } else {
            motionCharsRead = 0;   // discard oversized line
        }
    }
}

// Call every loop. Returns true when the status changed and the screen needs a redraw.
inline bool motionUpdate() {
    MotionStatus previous = motionStatus;
    motionReadSerial();
    if (millis() - motionLastStatusMs > MOTION_TIMEOUT_MS) motionStatus = CANNOT_ASSESS;
    return motionStatus != previous;
}

inline void motionDrawCentered(const char *text, int y, uint8_t size) {
    display.setTextSize(size);
    display.setCursor((display.width() - (int)strlen(text) * 6 * size) / 2, y);
    display.print(text);
    display.setTextSize(1);
}

// Draws into the buffer only; caller is responsible for display.display()
inline void drawMotionStatus() {
    if (motionStatus == FORM_GOOD) {
        motionDrawCentered("GOOD", 39, 2);
        motionDrawCentered("No major lean", 56, 1);
    } else if (motionStatus == FORM_BAD) {
        motionDrawCentered("BAD", 39, 2);
        motionDrawCentered("Large torso lean", 56, 1);
    } else {
        motionDrawCentered("CANNOT ASSESS", 42, 1);
        motionDrawCentered("Check camera/pose", 56, 1);
    }
}

#endif
