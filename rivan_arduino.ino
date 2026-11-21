/* AUTO-MOTION Tuesday display for Arduino UNO R4 Minima.
 * Python handles pose, calibration, decisions; Arduino only shows status.
 * UART-over-USB: 115200 baud, one ASCII line S,GOOD / S,BAD / S,UNKNOWN.
 * Default OLED assumption: 128x64 I2C SSD1306 at 0x3C.
 * If an SH1106: switch OLED_DRIVER to 2 and reupload.
 * If screen is not I2C 128x64, identify model before editing this sketch.
 */



 // to update the comments that were added, run this at the end in the vs code terminal
 // git add arduino/auto_motion_display/auto_motion_display.ino
 // git commit -m "Add explanatory comments to Arduino display code"
 // git push

#include <Arduino.h>
#include <Wire.h>
#include <U8g2lib.h>
#include <string.h>

#define OLED_DRIVER 1   // 1 = SSD1306 128x64 I2C; 2 = SH1106 128x64 I2C, if we change the OLED we're using, change this value, then compiel this code and run ita again
#define OLED_ADDR 0x3C // common I2C address; scanner confirms, when we eventually get the OLED, do the i2c_scanner.ino from online to chcek its adress so we can manually change this too.
// pre processor directive so that we can check the models we're using and change it depending on which OLED we're using, saves memory

#if OLED_DRIVER == 1
U8G2_SSD1306_128X64_NONAME_F_HW_I2C screen(U8G2_R0, U8X8_PIN_NONE); // no rotation and no reset pin (idk how googled it, they said to add)
#elif OLED_DRIVER == 2
U8G2_SH1106_128X64_NONAME_F_HW_I2C screen(U8G2_R0, U8X8_PIN_NONE); // screen object so we dont have to keep making functions, from library, member functions to make it easier we dont have to make our own
#else
#error Unsupported OLED_DRIVER // screen.____ accesses the member functions frm the ug8 thingy library that already defined the display class for the screen object
#endif

enum Status { CANNOT_ASSESS, FORM_GOOD, FORM_BAD }; // enum creates a new data type status, new data type status, three modes, 0,1,2 or cannotasses, form good, form bad, makes it easier to read
Status currentStatus = CANNOT_ASSESS; // status is data type, currentStatus is identifier, set to 0 or cannot_asses
char inputBuffer[30]; // char array so we can display text and convert the signal of S,GOOD for example into the array, charsRead tracks how many values we've stored into the array so far
uint8_t charsRead = 0;
unsigned long lastStatusMs = 0; // store timestamps in milliseconds, which is why we're using long
unsigned long lastDrawMs = 0;

void parsePacket(const char *line) { // updates status based on the message we get from the python script to the arduino, updates current excersise status.
// pointer to line so we can put an array here and then we can access the first 0 index value of the array
  if (strncmp(line, "S,", 2) != 0) return; // if the first two letters aren't "S," which is what it will sent for S,Good or S,Bad, then it just returns as theres been an error in sending the message from the python script to the arduino
    // prevents unrelated messages from being read as excersise status
  const char *value = line + 2; // moves pointer forward by two charectars to skip the "S," so now the pointer to value points to "GOOD" instead of line's "S,GOOD"

  if (strcmp(value, "GOOD") == 0) currentStatus = FORM_GOOD; // compares the rest of the string of value, to the second part of the function, 
  else if (strcmp(value, "BAD") == 0) currentStatus = FORM_BAD;
  else if (strcmp(value, "UNKNOWN") == 0) currentStatus = CANNOT_ASSESS; // sets the value based on what we're given
  else return; // if no signal, returns, prevents false reads or infinite loop
  lastStatusMs = millis(); // happens after the return so it only runs if the status is set
}

void readSerial() { // reads the singal so that we can interpret it with our parsePacket function
// python sends S,Good, the arduino stores it as an array, waits for \n before processing complete message
  while (Serial.available() > 0) { // serial is an object, serial.available checks how many bytes waiting to get processed, so if its greater than 0 theres something waiting to be processsed
  // if no availble byte to process it just skips the function call as its void no need to return anything
    char ch = (char) Serial.read(); // reads the first bye/char and stores it
    if (ch == '\r') continue; // incase it sends \r\n, continue is smth to tell it to keep going, skips the rest of the while loop but doesn't exit the function
    if (ch == '\n') { // end of the signal
      inputBuffer[charsRead] = '\0'; // adds a null to the end for functions like strcmp that need it to work
      parsePacket(inputBuffer); // call function on array which now has the values, updates currentStatus
      charsRead = 0; // resets
    } else if (charsRead < sizeof(inputBuffer) - 1) { // -1 so it can put \0 in the last spot, this whole thing just creates the array inputBuffer with the values of the ch from the signal. 
      inputBuffer[charsRead++] = ch; 
    } else {
      charsRead = 0; // discard oversized input; never overflow memory, avoid writin past the end of the array
    }
  }
}

void drawStatus() {
  screen.clearBuffer(); // from method function to clear the OLED
  screen.setFont(u8g2_font_6x12_tr); // font 
  screen.drawStr(0, 11, "AUTO-MOTION / SHOULDER"); // title
  screen.drawHLine(0, 16, 128); // horizontal line to make it look pretty :D

  if (currentStatus == FORM_GOOD) {
    screen.setFont(u8g2_font_logisoso20_tr);
    screen.drawStr(30, 46, "GOOD"); 
    screen.setFont(u8g2_font_6x12_tr); //draws the stuff
    screen.drawStr(4, 61, "No major lean detected"); // do we need these smaller mesages? filler messages for now, maybe get rid of them
  } else if (currentStatus == FORM_BAD) {
    screen.setFont(u8g2_font_logisoso20_tr);
    screen.drawStr(38, 46, "BAD");
    screen.setFont(u8g2_font_6x12_tr); // same thing
    screen.drawStr(4, 61, "Large torso lean");
  } else {
    screen.setFont(u8g2_font_6x12_tr);
    screen.drawStr(13, 35, "CANNOT ASSESS"); 
    screen.drawStr(10, 53, "Check camera/pose");
  }
  screen.sendBuffer(); // send it to the OLED
}

void setup() {
  Serial.begin(115200); // communication setting bits per second, python script uses it too, syncs the two
  Wire.begin(); // handle I2C connection
  screen.setI2CAddress(OLED_ADDR * 2);  // U8g2 expects a shifted address, sets adress to communicate w OLED , *2 is bit shifting it, format that the function wants ?!?
  screen.begin(); // initializes OLED, starts it 
  drawStatus(); // draws the status of CANNOT ASSES bc we assigned it to that earlier 
  lastDrawMs = millis(); // time since the arduino started
}

void loop() { // continously runs 
  readSerial(); // checks for new messages
  if (millis() - lastStatusMs > 1200) { // if there is a gap of larger than 1.2 seconds from concurrent messages, it senses a gap from the camera and says cannot asses (different than the drawing ms, its the time since signal)
    currentStatus = CANNOT_ASSESS;
  }
  if (millis() - lastDrawMs >= 150) { // refreshes it every 150 ms from drawing the screen.
    drawStatus(); // draws the status
    lastDrawMs = millis(); // refreshes the last draw
  }
}
