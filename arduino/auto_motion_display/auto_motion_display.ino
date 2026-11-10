/* AUTO-MOTION Tuesday display for Arduino UNO R4 Minima.
 * Python handles pose, calibration, decisions; Arduino only shows status.
 * UART-over-USB: 115200 baud, one ASCII line S,GOOD / S,BAD / S,UNKNOWN.
 * Default OLED assumption: 128x64 I2C SSD1306 at 0x3C.
 * If an SH1106: switch OLED_DRIVER to 2 and reupload.
 * If screen is not I2C 128x64, identify model before editing this sketch.
 */
#include <Arduino.h>
#include <Wire.h>
#include <U8g2lib.h>
#include <string.h>

#define OLED_DRIVER 1   // 1 = SSD1306 128x64 I2C; 2 = SH1106 128x64 I2C
#define OLED_ADDR 0x3C // common I2C address; scanner confirms

#if OLED_DRIVER == 1
U8G2_SSD1306_128X64_NONAME_F_HW_I2C screen(U8G2_R0, U8X8_PIN_NONE);
#elif OLED_DRIVER == 2
U8G2_SH1106_128X64_NONAME_F_HW_I2C screen(U8G2_R0, U8X8_PIN_NONE);
#else
#error Unsupported OLED_DRIVER
#endif

enum Status { CANNOT_ASSESS, FORM_GOOD, FORM_BAD };
Status currentStatus = CANNOT_ASSESS;
char inputBuffer[30];
uint8_t charsRead = 0;
unsigned long lastStatusMs = 0;
unsigned long lastDrawMs = 0;

void parsePacket(const char *line) {
  if (strncmp(line, "S,", 2) != 0) return;
  const char *value = line + 2;
  if (strcmp(value, "GOOD") == 0) currentStatus = FORM_GOOD;
  else if (strcmp(value, "BAD") == 0) currentStatus = FORM_BAD;
  else if (strcmp(value, "UNKNOWN") == 0) currentStatus = CANNOT_ASSESS;
  else return;
  lastStatusMs = millis();
}

void readSerial() {
  while (Serial.available() > 0) {
    char ch = (char) Serial.read();
    if (ch == '\r') continue;
    if (ch == '\n') {
      inputBuffer[charsRead] = '\0';
      parsePacket(inputBuffer);
      charsRead = 0;
    } else if (charsRead < sizeof(inputBuffer) - 1) {
      inputBuffer[charsRead++] = ch;
    } else {
      charsRead = 0; // discard oversized input; never overflow memory
    }
  }
}

void drawStatus() {
  screen.clearBuffer();
  screen.setFont(u8g2_font_6x12_tr);
  screen.drawStr(0, 11, "AUTO-MOTION / SHOULDER");
  screen.drawHLine(0, 16, 128);

  if (currentStatus == FORM_GOOD) {
    screen.setFont(u8g2_font_logisoso20_tr);
    screen.drawStr(30, 46, "GOOD");
    screen.setFont(u8g2_font_6x12_tr);
    screen.drawStr(4, 61, "No major lean detected");
  } else if (currentStatus == FORM_BAD) {
    screen.setFont(u8g2_font_logisoso20_tr);
    screen.drawStr(38, 46, "BAD");
    screen.setFont(u8g2_font_6x12_tr);
    screen.drawStr(4, 61, "Large torso lean");
  } else {
    screen.setFont(u8g2_font_6x12_tr);
    screen.drawStr(13, 35, "CANNOT ASSESS");
    screen.drawStr(10, 53, "Check camera/pose");
  }
  screen.sendBuffer();
}

void setup() {
  Serial.begin(115200);
  Wire.begin();
  screen.setI2CAddress(OLED_ADDR * 2);  // U8g2 expects a shifted address
  screen.begin();
  drawStatus();
  lastDrawMs = millis();
}

void loop() {
  readSerial();
  if (millis() - lastStatusMs > 1200) {
    currentStatus = CANNOT_ASSESS;
  }
  if (millis() - lastDrawMs >= 150) {
    drawStatus();
    lastDrawMs = millis();
  }
}
