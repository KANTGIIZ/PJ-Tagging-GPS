#include <TinyGPS++.h>
#include <HardwareSerial.h>
#include <WiFi.h>
#include <HTTPClient.h>

// ================= GPS =================
TinyGPSPlus gps;
HardwareSerial SerialGPS(2);

#define RXD2 16   // GPS TX -> ESP32 RX2
#define TXD2 17   // GPS RX -> ESP32 TX2
#define LED  2    // LED แสดงสถานะ GPS

// ================= WiFi =================
const char* ssid     = "Piramid Solution";
const char* password = "0837777740";

// ================= Server =================
String serverName = "http://192.168.1.50:5000/gps";
String deviceName = "ESP32-GPS-01";

// ================= Timer =================
unsigned long lastBlink = 0;
unsigned long lastSend  = 0;
bool ledState = false;

const unsigned long blinkInterval = 500;   // LED กระพริบ 500ms
const unsigned long sendInterval  = 5000;  // ส่งข้อมูลทุก 5 วินาที

// ================= Setup =================
void setup() {
  Serial.begin(115200);
  SerialGPS.begin(9600, SERIAL_8N1, RXD2, TXD2);

  pinMode(LED, OUTPUT);
  digitalWrite(LED, LOW);

  // Connect WiFi
  WiFi.begin(ssid, password);
  Serial.print("Connecting WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi Connected: " + WiFi.localIP().toString());
}

// ================= Loop =================
void loop() {
  // อ่านข้อมูล GPS ตลอดเวลา
  while (SerialGPS.available()) {
    gps.encode(SerialGPS.read());
  }

  bool gpsFixed = gps.location.isValid() && gps.location.isUpdated();

  // ================= GPS FIX =================
  if (gpsFixed) {
    digitalWrite(LED, HIGH);   // LED ติดค้าง

    double lat = gps.location.lat();
    double lon = gps.location.lng();
    int sats = gps.satellites.isValid() ? gps.satellites.value() : 0;

    Serial.println("===== GPS FIXED =====");
    Serial.printf("Lat: %.6f | Lon: %.6f | Sats: %d\n", lat, lon, sats);

    // ส่งข้อมูลทุก 5 วินาที
    if (millis() - lastSend >= sendInterval) {
      lastSend = millis();

      if (WiFi.status() == WL_CONNECTED) {
        HTTPClient http;
        http.begin(serverName);
        http.addHeader("Content-Type", "application/json");

        String json = "{";
        json += "\"device-name\":\"" + deviceName + "\",";
        json += "\"lat\":" + String(lat, 6) + ",";
        json += "\"lon\":" + String(lon, 6) + ",";
        json += "\"satellites\":" + String(sats);
        json += "}";

        int httpCode = http.POST(json);
        Serial.printf("HTTP POST: %d\n", httpCode);
        http.end();
      }
    }
  }
  // ================= GPS NOT FIX =================
  else {
    Serial.println("Waiting for GPS fix...");

    // LED กระพริบ
    if (millis() - lastBlink >= blinkInterval) {
      lastBlink = millis();
      ledState = !ledState;
      digitalWrite(LED, ledState);
    }
  }
}
