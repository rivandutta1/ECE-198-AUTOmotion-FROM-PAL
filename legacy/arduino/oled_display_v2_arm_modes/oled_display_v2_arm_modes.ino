/* AUTO-MOTION ARM STUDIO -- Arduino UNO R4 Minima + 128x64 I2C OLED.
 * Python computes all exercise feedback. Arduino only displays it.
 * USB serial: 115200 baud. New protocol:
 *   F,CURL,GOOD,OK,3 followed by newline
 *   F,PUSHDOWN,BAD,LEAN,3 followed by newline
 * Shoulder/chest experimental modes also use F packets; no press rep count.
 * Original S,GOOD/BAD/UNKNOWN packets still work for teammates' demos.
 * Display falls back to CANNOT ASSESS if USB messages stop for 1.2s.
 * If using SH1106 replace OLED_DRIVER 1 with 2.
 */
#include <Arduino.h>
#include <Wire.h>
#include <U8g2lib.h>
#include <string.h>
#include <stdlib.h>

#define OLED_DRIVER 1    // 1 = SSD1306; 2 = SH1106
#define OLED_ADDR 0x3C   // common OLED I2C address; use i2c_scanner.ino to check

#if OLED_DRIVER == 1
U8G2_SSD1306_128X64_NONAME_F_HW_I2C screen(U8G2_R0, U8X8_PIN_NONE);
#elif OLED_DRIVER == 2
U8G2_SH1106_128X64_NONAME_F_HW_I2C screen(U8G2_R0, U8X8_PIN_NONE);
#else
#error OLED_DRIVER must be 1 or 2
#endif

enum FormStatus { FORM_UNKNOWN, FORM_GOOD, FORM_BAD };
FormStatus status = FORM_UNKNOWN;
char exercise[12] = "CURL";
char issue[10] = "CAL";
unsigned int reps = 0;
char inputBuffer[64];
uint8_t bytesRead = 0;
bool overflowed = false;
unsigned long lastPacketMs = 0;
unsigned long lastDrawMs = 0;

bool validIssue(const char *x) {
  const char *valid[] = {"OK","TRACK","CAL","START","IDLE","LEAN","ARM","ROM","FORM"};
  for (unsigned int i = 0; i < sizeof(valid)/sizeof(valid[0]); ++i)
    if (strcmp(x, valid[i]) == 0) return true;
  return false;
}

bool parseStatus(const char *text, FormStatus *out) {
  if (strcmp(text, "GOOD") == 0) *out = FORM_GOOD;
  else if (strcmp(text, "BAD") == 0) *out = FORM_BAD;
  else if (strcmp(text, "UNKNOWN") == 0) *out = FORM_UNKNOWN;
  else return false;
  return true;
}

void parsePacket(char *line) {
  char *context;
  char *kind = strtok_r(line, ",", &context);
  if (kind == NULL) return;
  if (strcmp(kind, "S") == 0) {
    char *value = strtok_r(NULL, ",", &context);
    if (value == NULL || strtok_r(NULL, ",", &context) != NULL) return;
    FormStatus fresh;
    if (!parseStatus(value, &fresh)) return;
    status = fresh;
    strcpy(issue, fresh == FORM_UNKNOWN ? "TRACK" : "OK");
    lastPacketMs = millis();
    return;
  }
  if (strcmp(kind, "F") != 0) return;
  char *ex = strtok_r(NULL, ",", &context);
  char *value = strtok_r(NULL, ",", &context);
  char *code = strtok_r(NULL, ",", &context);
  char *number = strtok_r(NULL, ",", &context);
  if (!ex || !value || !code || !number || strtok_r(NULL, ",", &context)) return;
  if (strcmp(ex, "CURL") != 0 && strcmp(ex, "PUSHDOWN") != 0 &&
      strcmp(ex, "SHOULDER") != 0 && strcmp(ex, "CHEST") != 0) return;
  if (!validIssue(code)) return;
  FormStatus fresh;
  if (!parseStatus(value, &fresh)) return;
  if (*number == '\0') return;
  for (char *p = number; *p; ++p) if (*p < '0' || *p > '9') return;
  unsigned long count = strtoul(number, NULL, 10);
  if (count > 9999) return;
  strcpy(exercise, ex);
  strcpy(issue, code);
  reps = (unsigned int)count;
  status = fresh;
  lastPacketMs = millis();
}

void readSerial() {
  while (Serial.available()) {
    char ch = (char)Serial.read();
    if (ch == '\r') continue;
    if (ch == '\n') {
      if (!overflowed) {
        inputBuffer[bytesRead] = '\0';
        parsePacket(inputBuffer);
      }
      bytesRead = 0;
      overflowed = false;
    } else if (overflowed) {
      // Drop the rest of the line without risking a partial valid packet.
    } else if (bytesRead < sizeof(inputBuffer) - 1) {
      inputBuffer[bytesRead++] = ch;
    } else {
      overflowed = true;
    }
  }
}

const char *issueText(const char *code) {
  if (strcmp(code, "LEAN") == 0) return "Torso swinging";
  if (strcmp(code, "ARM") == 0) return "Check arm position";
  if (strcmp(code, "ROM") == 0) return "Partial range";
  if (strcmp(code, "FORM") == 0) return "Rep had bad form";
  if (strcmp(code, "CAL") == 0) return "Calibrate: press C";
  if (strcmp(code, "TRACK") == 0) return "Check camera view";
  if (strcmp(code, "START") == 0) return "Return to start";
  if (strcmp(code, "IDLE") == 0) return "Start a rep";
  return "Movement tracked";
}

void drawStatus() {
  screen.clearBuffer();
  screen.setFont(u8g2_font_6x12_tr);
  screen.drawStr(0, 11, "AUTO-MOTION / ARM STUDIO");
  screen.drawHLine(0, 15, 128);
  screen.drawStr(0, 26, exercise);
  char count[20];
  if (strcmp(exercise, "SHOULDER") == 0 || strcmp(exercise, "CHEST") == 0) {
    snprintf(count, sizeof(count), "2D FORM");
  } else {
    snprintf(count, sizeof(count), "REPS %u", reps);
  }
  screen.drawStr(69, 26, count);
  if (status == FORM_GOOD) {
    screen.setFont(u8g2_font_ncenB14_tr);
    screen.drawStr(35, 45, "GOOD");
  } else if (status == FORM_BAD) {
    screen.setFont(u8g2_font_ncenB14_tr);
    screen.drawStr(44, 45, "BAD");
  } else {
    screen.setFont(u8g2_font_6x12_tr);
    screen.drawStr(15, 43, "CANNOT ASSESS");
  }
  screen.setFont(u8g2_font_6x12_tr);
  screen.drawStr(0, 62, issueText(issue));
  screen.sendBuffer();
}

void setup() {
  Serial.begin(115200);
  Wire.begin();
  screen.setI2CAddress(OLED_ADDR * 2); // U8g2 uses shifted address
  screen.begin();
  drawStatus();
  lastDrawMs = millis();
}

void loop() {
  readSerial();
  if (millis() - lastPacketMs > 1200) {
    status = FORM_UNKNOWN;
    strcpy(issue, "TRACK");
  }
  if (millis() - lastDrawMs >= 150) {
    drawStatus();
    lastDrawMs = millis();
  }
}
