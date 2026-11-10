// Use only if the OLED is I2C and the type/address are unknown.
#include <Wire.h>
void setup(){
  Serial.begin(115200);
  Wire.begin();
}
void loop(){
  Serial.println("I2C scan:");
  for (byte address=1; address<127; address++) {
    Wire.beginTransmission(address);
    if (Wire.endTransmission()==0) {
      Serial.print("Found 0x"); Serial.println(address, HEX);
    }
  }
  delay(2500);
}
