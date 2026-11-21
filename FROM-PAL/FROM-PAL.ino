#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include "auto_motion_display.h"

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);
bool oledReady = false;

// I2C with ultrasonic sensor
const int TRIG_PIN = 5;
const int ECHO_PIN = 6;

// Debounced button handling
const unsigned long DEBOUNCE_MS = 50;

struct Button {
    uint8_t pin;
    bool stableState; // debounced "is pressed"
    bool lastReading; // raw reading from last pass
    unsigned long lastChange; // when the raw reading last changed
};

Button button = {2, false, false, 0};   // Mode switch

enum DisplayMode { SHOULDER_MODE, CHEST_MODE, DESKTOP_MODE };
DisplayMode displayMode = CHEST_MODE;

int maxChestROM = 0;
int maxShoulderROM = 0;
int repCountChest = 0;
int repCountShoulder = 0;

int startingDistance = 0;

// Automatic turning-point detection
const int MAX_JUMP_CM = 15;                  // readings further than this from the last one are treated as noise
const int MIN_MOVE_CM = 8;                   // must reverse by this much to confirm a turning point (raise if still over-counting)
const uint8_t MAX_REJECTS = 5;               // accept a jump anyway after this many in a row
const unsigned long SAMPLE_INTERVAL_MS = 50;

int lastDistance = 0;
int extremeDistance = 0;
int direction = 0;                           // 1 = moving away, -1 = moving closer, 0 = not yet moving
uint8_t rejectCount = 0;
int recent[3];                               // last 3 accepted readings, median is used to remove spikes
uint8_t recentCount = 0;
uint8_t recentIndex = 0;
unsigned long lastSampleMs = 0;

// Returns true exactly once per press, after the signal has settled
bool wasPressed(Button &b) {
    bool reading = (digitalRead(b.pin) == LOW);   // active-low

    // Any flicker restarts the timer
    if (reading != b.lastReading) {
        b.lastChange = millis();
        b.lastReading = reading;
    }

    // Reading has been steady long enough, and differs from the accepted state
    if ((millis() - b.lastChange) > DEBOUNCE_MS && reading != b.stableState) {
        b.stableState = reading;
        return reading; // true on press, false on release
    }
    return false;
}

void setup() {
    Serial.begin(115200);
    pinMode(button.pin, INPUT_PULLUP);

    pinMode(TRIG_PIN, OUTPUT);
    pinMode(ECHO_PIN, INPUT);
    startingDistance = getDistance();
    resetTracking();

    Wire.begin();
    for (uint8_t address = 0x3C; address <= 0x3D; address++) {
        Wire.beginTransmission(address);
        if (Wire.endTransmission() == 0) {
            oledReady = display.begin(SSD1306_SWITCHCAPVCC, address, true, false);
            break;
        }
    }
    if (!oledReady) Serial.println("OLED unavailable: check SSD1306 wiring and I2C address");
    updateDisplay();
}

void loop() {
    const bool wasConnected = motionConnected;
    const bool feedbackChanged = motionUpdate();
    const DisplayMode previousMode = displayMode;

    if (wasPressed(button)) {
        switch (displayMode) {
            case SHOULDER_MODE: displayMode = CHEST_MODE; break;
            case CHEST_MODE: displayMode = DESKTOP_MODE; break;
            case DESKTOP_MODE: displayMode = SHOULDER_MODE; break;
        }
        Serial.println("Switched modes");
    } else if (!wasConnected && motionConnected) {
        // Auto-select Desktop once per connection. The button can leave it
        // while packets continue to arrive.
        displayMode = DESKTOP_MODE;
    }

    if (displayMode != previousMode) {
        if (displayMode != DESKTOP_MODE) {
            startingDistance = getDistance();
            resetTracking();
        }
        updateDisplay();
    } else if (displayMode == DESKTOP_MODE && feedbackChanged) {
        updateDisplay();
    }

    if (displayMode != DESKTOP_MODE && millis() - lastSampleMs >= SAMPLE_INTERVAL_MS) {
        lastSampleMs = millis();
        trackDistance();
    }
}

void resetTracking() {
    lastDistance = startingDistance;
    extremeDistance = startingDistance;
    direction = 0;
    rejectCount = 0;
    recentCount = 0;
    recentIndex = 0;
}

// Registers a turning point exactly as a press of the old rep button did
void registerRep(int currentDistance) {
    int difference = abs(startingDistance - currentDistance);
    startingDistance = currentDistance;

    const bool isChestPress = displayMode == CHEST_MODE;
    if (isChestPress) repCountChest++;
    else repCountShoulder++;

    if (isChestPress && difference > maxChestROM) {
        maxChestROM = difference;
        Serial.print("Chest ROM: ");
        Serial.println(maxChestROM);
    }
    if (!isChestPress && difference > maxShoulderROM) {
        maxShoulderROM = difference;
        Serial.print("Shoulder ROM: ");
        Serial.println(maxShoulderROM);
    }
    updateDisplay();
}

void trackDistance() {
    int d = getDistance();
    if (d <= 0) return;   // sensor timeout

    // Ignore readings that jump too far from the last one
    if (abs(d - lastDistance) > MAX_JUMP_CM && rejectCount < MAX_REJECTS) {
        rejectCount++;
        return;
    }
    rejectCount = 0;
    lastDistance = d;

    // Median of the last 3 readings
    recent[recentIndex] = d;
    recentIndex = (recentIndex + 1) % 3;
    if (recentCount < 3) recentCount++;
    if (recentCount < 3) return;
    int a = recent[0], b = recent[1], c = recent[2];
    d = max(min(a, b), min(max(a, b), c));

    if (direction == 0) {
        if (d - startingDistance >= MIN_MOVE_CM) direction = 1;
        else if (startingDistance - d >= MIN_MOVE_CM) direction = -1;
        else return;
        extremeDistance = d;
        return;
    }

    if (direction == 1) {
        if (d > extremeDistance) extremeDistance = d;
        else if (extremeDistance - d >= MIN_MOVE_CM) {   // peaked, now coming back
            registerRep(extremeDistance);
            direction = -1;
            extremeDistance = d;
        }
    } else {
        if (d < extremeDistance) extremeDistance = d;
        else if (d - extremeDistance >= MIN_MOVE_CM) {   // bottomed out, now moving away
            registerRep(extremeDistance);
            direction = 1;
            extremeDistance = d;
        }
    }
}

void updateDisplay() {
    if (!oledReady) return;
    display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);

    if (displayMode == DESKTOP_MODE) {
        drawDesktopFeedback();
        display.display();
        return;
    }

    // Line 1: Chest
    display.setCursor(0, 10);
    display.print(displayMode == CHEST_MODE ? ">Chest: " : " Chest: ");
    display.print(maxChestROM);
    display.print("cm; ");
    display.print(repCountChest / 2);

    // Line 2: Shoulder
    display.setCursor(0, 30);
    display.print(displayMode == SHOULDER_MODE ? ">Shoulder: " : " Shoulder: ");
    display.print(maxShoulderROM);
    display.print("cm; ");
    display.print(repCountShoulder / 2);

    display.display();
}

/*
 * Returns the distance measured by the HC-SR04 in cm
 */
int getDistance() {
    digitalWrite(TRIG_PIN, LOW);
    delayMicroseconds(2);
    digitalWrite(TRIG_PIN, HIGH);
    delayMicroseconds(10);
    digitalWrite(TRIG_PIN, LOW);

    // supplier recommended waiting time before taking a new measurement
    delayMicroseconds(60);
    long duration = pulseIn(ECHO_PIN, HIGH, 30000);   // 30 ms timeout so the loop never hangs
    return duration * 0.034 / 2.0; // Distance in cm
}
