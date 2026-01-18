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

// ================= WiFi =================
const char* ssid     = "LukMuoo_HA";
const char* password = "Smartpiglet";

// ================= Server =================
String serverURL  = "https://projectmyluggie.pythonanywhere.com/update";
String deviceName = "LUGGIE-01";

// ================= Timer =================
unsigned long lastBlink = 0;
unsigned long lastSend  = 0;
bool ledState = false;

const unsigned long blinkInterval = 500;
const unsigned long sendInterval  = 30000;   // 10 วินาที (เหมือน Python)

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

  bool gpsFixed = gps.location.isValid() && gps.location.isUpdated();

  // ================= GPS FIX =================
  if (gpsFixed) {
    digitalWrite(LED, HIGH);

    double lat = gps.location.lat();
    double lon = gps.location.lng();
    int sats = gps.satellites.isValid() ? gps.satellites.value() : 0;

    Serial.printf("GPS FIX: %.6f, %.6f | SAT: %d\n", lat, lon, sats);

    if (millis() - lastSend >= sendInterval) {
      lastSend = millis();

      if (WiFi.status() == WL_CONNECTED) {
        HTTPClient http;
        http.begin(serverURL);
        http.addHeader("Content-Type", "application/json");

        // === JSON FORMAT SAME AS PYTHON ===
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
    Serial.println("Waiting for GPS fix...");

    if (millis() - lastBlink >= blinkInterval) {
      lastBlink = millis();
      ledState = !ledState;
      digitalWrite(LED, ledState);
    }
  }
}
