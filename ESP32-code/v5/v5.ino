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

// ================= Timing =================
unsigned long lastBlink     = 0;
unsigned long lastSend      = 0;
unsigned long lastHeartbeat = 0;
unsigned long lastFixTime   = 0;
unsigned long lastLog       = 0;

bool ledState = false;

// ================= Config =================
const unsigned long blinkInterval     = 500;    // LED กระพริบ
const unsigned long sendInterval      = 30000;  // ส่งเมื่อขยับ (ขั้นต่ำ)
const unsigned long heartbeatInterval = 30000;  // กัน server offline
const unsigned long fixTimeout        = 3000;   // FIX timeout
const unsigned long logInterval        = 2000;  // จำกัด log

const double minDistance = 8.0; // เมตร (กัน GPS noise)

// ================= Last sent position =================
double lastSentLat = 0;
double lastSentLon = 0;
bool hasLastSent = false;

// ================= Setup =================
void setup() {
  Serial.begin(115200);
  SerialGPS.begin(9600, SERIAL_8N1, RXD2, TXD2);

  pinMode(LED, OUTPUT);
  digitalWrite(LED, LOW);

  WiFi.setAutoReconnect(true);
  WiFi.persistent(true);

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
  // ---------- Read GPS ----------
  while (SerialGPS.available()) {
    gps.encode(SerialGPS.read());
  }

  // ---------- Update FIX time ----------
  if (gps.location.isValid()) {
    lastFixTime = millis();
  }

  bool gpsFixed = (millis() - lastFixTime) < fixTimeout;

  // ---------- GPS FIX ----------
  if (gpsFixed) {
    digitalWrite(LED, HIGH);

    double lat = gps.location.lat();
    double lon = gps.location.lng();
    int sats   = gps.satellites.isValid() ? gps.satellites.value() : 0;

    // จำกัด log
    if (millis() - lastLog >= logInterval) {
      lastLog = millis();
      Serial.printf("GPS FIX: %.6f, %.6f | SAT: %d\n", lat, lon, sats);
    }

    // ---------- Distance check ----------
    double distance = 0;
    if (hasLastSent) {
      distance = TinyGPSPlus::distanceBetween(
        lat, lon,
        lastSentLat, lastSentLon
      );
    }

    bool movedEnough  = !hasLastSent || distance >= minDistance;
    bool heartbeatDue = millis() - lastHeartbeat >= heartbeatInterval;

    // ---------- Send condition ----------
    if ((movedEnough && millis() - lastSend >= sendInterval) || heartbeatDue) {

      if (WiFi.status() != WL_CONNECTED) {
        WiFi.reconnect();
      }

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
        Serial.printf("POST %d | distance=%.2fm | heartbeat=%s\n",
                      code, distance, heartbeatDue ? "YES" : "NO");
        http.end();

        lastSentLat = lat;
        lastSentLon = lon;
        hasLastSent = true;
        lastSend = millis();
        lastHeartbeat = millis();
      }
    }
  }

  // ---------- GPS NOT FIX ----------
  else {
    if (millis() - lastLog >= logInterval) {
      lastLog = millis();
      Serial.println("Waiting for GPS fix...");
    }

    if (millis() - lastBlink >= blinkInterval) {
      lastBlink = millis();
      ledState = !ledState;
      digitalWrite(LED, ledState);
    }
  }
}
