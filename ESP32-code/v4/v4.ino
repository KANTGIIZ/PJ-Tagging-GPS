#include <TinyGPS++.h>
#include <HardwareSerial.h>
#include <WiFi.h>
#include <HTTPClient.h>

// ================= GPS =================
TinyGPSPlus gps;
HardwareSerial SerialGPS(2);

#define RXD2 16
#define TXD2 17
#define LED  2

// ================= Log =================
unsigned long lastLog = 0;
const unsigned long logInterval = 2000; // 2 วินาที

// ================= WiFi =================
const char* ssid     = "LukMuoo_HA";
const char* password = "Smartpiglet";

// ================= Server =================
String serverURL  = "https://projectmyluggie.pythonanywhere.com/update";
String deviceName = "LUGGIE-01";

// ================= Timer =================
unsigned long lastBlink   = 0;
unsigned long lastSend    = 0;
unsigned long lastFixTime = 0;

bool ledState = false;

const unsigned long blinkInterval = 500;
const unsigned long sendInterval  = 30000; // 30 วินาที
const unsigned long fixTimeout    = 3000;  // FIX timeout 3 วินาที

// ================= Setup =================
void setup() {
  Serial.begin(115200);
  SerialGPS.begin(9600, SERIAL_8N1, RXD2, TXD2);

  pinMode(LED, OUTPUT);
  digitalWrite(LED, LOW);

  // WiFi connect
  WiFi.begin(ssid, password);
  Serial.print("Connecting WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected: " + WiFi.localIP().toString());
}

// ================= Loop =================
void loop() {
  // อ่าน GPS ตลอดเวลา
  while (SerialGPS.available()) {
    gps.encode(SerialGPS.read());
  }

  // อัปเดตเวลา FIX ล่าสุด (ไม่ใช้ isUpdated)
  if (gps.location.isValid()) {
    lastFixTime = millis();
  }

  // FIX จริง = ยังไม่ timeout
  bool gpsFixed = (millis() - lastFixTime) < fixTimeout;

  // ================= GPS FIX =================
  if (gpsFixed) {
    digitalWrite(LED, HIGH);

    double lat = gps.location.lat();
    double lon = gps.location.lng();
    int sats   = gps.satellites.isValid() ? gps.satellites.value() : 0;

    // Log แบบไม่รัว
    if (millis() - lastLog >= logInterval) {
      lastLog = millis();
      Serial.printf("GPS FIX: %.6f, %.6f | SAT: %d\n", lat, lon, sats);
    }

    // ส่งข้อมูลทุก sendInterval
    if (millis() - lastSend >= sendInterval) {
      lastSend = millis();

      if (WiFi.status() == WL_CONNECTED) {
        HTTPClient http;
        http.begin(serverURL);
        http.addHeader("Content-Type", "application/json");

        String json = "{";
        json += "\"device_name\":\"" + deviceName + "\",";
        json += "\"ip_address\":\"" + WiFi.localIP().toString() + "\",";
        json += "\"lat\":" + String(lat, 6) + ",";
        json += "\"lon\":" + String(lon, 6) + ",";
        json += "\"satellites\":" + String(sats);
        json += "}";

        int code = http.POST(json);
        Serial.printf("POST %d\n", code);
        http.end();
      }
    }
  }
  // ================= GPS NOT FIX =================
  else {
    // Log แบบจำกัดความถี่
    if (millis() - lastLog >= logInterval) {
      lastLog = millis();
      Serial.println("Waiting for GPS fix...");
    }

    // LED กระพริบ
    if (millis() - lastBlink >= blinkInterval) {
      lastBlink = millis();
      ledState = !ledState;
      digitalWrite(LED, ledState);
    }
  }
}
