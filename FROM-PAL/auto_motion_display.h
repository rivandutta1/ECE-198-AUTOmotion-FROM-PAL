#ifndef AUTO_MOTION_DISPLAY_H
#define AUTO_MOTION_DISPLAY_H

#include <Arduino.h>
#include <string.h>
#include <Adafruit_SSD1306.h>

extern Adafruit_SSD1306 display;

enum MotionStatus { CANNOT_ASSESS, FORM_GOOD, FORM_BAD };
enum MotionExercise { NO_ARM_EXERCISE, CURL, PUSHDOWN };

static MotionStatus motionStatus = CANNOT_ASSESS;
static MotionExercise motionExercise = NO_ARM_EXERCISE;
static unsigned int motionReps = 0;
static bool motionConnected = false;
static char motionBuffer[30];
static uint8_t motionCharsRead = 0;
static bool motionDiscardLine = false;
static unsigned long motionLastStatusMs = 0;

const unsigned long MOTION_TIMEOUT_MS = 1200;

inline bool motionParseStatus(const char *value, MotionStatus &status) {
    if (strcmp(value, "GOOD") == 0) status = FORM_GOOD;
    else if (strcmp(value, "BAD") == 0) status = FORM_BAD;
    else if (strcmp(value, "UNKNOWN") == 0) status = CANNOT_ASSESS;
    else return false;
    return true;
}

inline void motionParsePacket(char *line) {
    MotionStatus status;
    if (strncmp(line, "S,", 2) == 0) {
        if (!motionParseStatus(line + 2, status)) return;
        motionExercise = NO_ARM_EXERCISE;
    } else if (strncmp(line, "F,", 2) == 0) {
        char *fields[] = {line + 2, nullptr, nullptr, nullptr};
        for (uint8_t i = 1; i < 4; i++) {
            char *comma = strchr(fields[i - 1], ',');
            if (!comma) return;
            *comma = '\0';
            fields[i] = comma + 1;
        }
        MotionExercise exercise;
        if (strcmp(fields[0], "CURL") == 0) exercise = CURL;
        else if (strcmp(fields[0], "PUSHDOWN") == 0) exercise = PUSHDOWN;
        else return;
        if (!motionParseStatus(fields[1], status)) return;

        const char *issues[] = {"OK", "TRACK", "CAL", "START", "IDLE",
                                "LEAN", "ARM", "ROM", "FORM"};
        bool validIssue = false;
        for (const char *issue : issues) {
            if (strcmp(fields[2], issue) == 0) {
                validIssue = true;
                break;
            }
        }
        if (!validIssue) return;

        size_t digits = strlen(fields[3]);
        if (digits == 0 || digits > 4) return;
        unsigned int reps = 0;
        for (const char *digit = fields[3]; *digit; digit++) {
            if (*digit < '0' || *digit > '9') return;
            reps = reps * 10 + (*digit - '0');
        }
        motionExercise = exercise;
        motionReps = reps;
    } else {
        return;
    }
    motionStatus = status;
    motionConnected = true;
    motionLastStatusMs = millis();
}

inline void motionReadSerial() {
    while (Serial.available() > 0) {
        char ch = (char) Serial.read();
        if (ch == '\r') continue;
        if (ch == '\n') {
            if (!motionDiscardLine) {
                motionBuffer[motionCharsRead] = '\0';
                motionParsePacket(motionBuffer);
            }
            motionCharsRead = 0;
            motionDiscardLine = false;
        } else if (!motionDiscardLine) {
            if (ch >= ' ' && ch <= '~' && motionCharsRead < sizeof(motionBuffer) - 1) {
                motionBuffer[motionCharsRead++] = ch;
            } else {
                motionDiscardLine = true;
            }
        }
    }
}

// Connection, exercise, status, and reps all affect the Desktop display.
inline bool motionUpdate() {
    bool wasConnected = motionConnected;
    MotionStatus previousStatus = motionStatus;
    MotionExercise previousExercise = motionExercise;
    unsigned int previousReps = motionReps;
    motionReadSerial();
    if (motionConnected && millis() - motionLastStatusMs >= MOTION_TIMEOUT_MS) {
        motionConnected = false;
        motionStatus = CANNOT_ASSESS;
        motionExercise = NO_ARM_EXERCISE;
    }
    return motionConnected != wasConnected || motionStatus != previousStatus ||
           motionExercise != previousExercise ||
           (motionExercise != NO_ARM_EXERCISE && motionReps != previousReps);
}

inline void motionDrawCentered(const char *text, int y, uint8_t size) {
    display.setTextSize(size);
    display.setCursor((display.width() - (int)strlen(text) * 6 * size) / 2, y);
    display.print(text);
    display.setTextSize(1);
}

inline void drawDesktopFeedback() {
    if (!motionConnected) {
        motionDrawCentered("DESKTOP", 4, 1);
        motionDrawCentered("NO CONNECTION", 25, 1);
        motionDrawCentered("Waiting for app", 42, 1);
        return;
    }

    const char *title = "DESKTOP";
    if (motionExercise == CURL) title = "BICEP CURL";
    else if (motionExercise == PUSHDOWN) title = "TRICEP PUSHDOWN";
    motionDrawCentered(title, 4, 1);

    const char *label = motionStatus == FORM_GOOD ? "GOOD" :
                        motionStatus == FORM_BAD ? "BAD" : "UNKNOWN";
    motionDrawCentered(label, 23, 2);
    if (motionExercise != NO_ARM_EXERCISE) {
        display.setCursor(0, 51);
        display.print("Reps: ");
        display.print(motionReps);
    }
}

#endif
