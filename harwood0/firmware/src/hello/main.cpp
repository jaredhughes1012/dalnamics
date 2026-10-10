// Connectivity check: joins WiFi and serves the protocol over TCP and serial, like the robot
// firmware, but touches no pins or I2C, so it is safe on a bare Uno. Motion commands are
// accepted and ignored; `state` reports the arm parked and the track unhomed.
// Build and flash with `make flash-hello`, then `make check-robot`.

#include <Arduino.h>
#include <WiFiS3.h>

#include "config.h"
#include "motion.h"
#include "protocol.h"

#if __has_include("secrets.h")
#include "secrets.h"
#else
#error "Missing include/secrets.h: copy include/secrets.example.h and set WiFi credentials"
#endif

namespace {

WiFiServer server(kTcpPort);
WiFiClient client;
std::string clientLine;
std::string serialLine;
uint32_t requests = 0;

uint32_t uptimeMs() { return millis(); }
void ignoreStop() {}
void ignoreDrive(const protocol::Drive&) {}
void ignoreArm(const protocol::ArmTargets&) {}
void ignoreTrack(float) {}
void ignoreHome() {}

void parkedState(protocol::State& s) {
  s.drive = protocol::Drive{0, 0, 0, 0};
  s.arm_enabled = false;
  for (int j = 0; j < motion::kJointCount; j++)
    s.joints[j] = s.joint_targets[j] = motion::kParkPose[j];
  s.track_homed = false;
  s.track_homing = false;
  s.track_x = s.track_target = 0;
}

const protocol::Hooks hooks{uptimeMs,    ignoreStop, ignoreDrive, ignoreArm,
                            ignoreTrack, ignoreHome, parkedState};

bool readLine(char c, std::string& line) {
  if (c == '\n') return !line.empty();
  if (c != '\r') line += c;
  return false;
}

std::string dispatch(const std::string& request) {
  requests++;
  return protocol::handle(request, hooks);
}

void pollTcp() {
  WiFiClient incoming = server.accept();
  if (incoming) {
    if (client) client.stop();
    client = incoming;
    clientLine.clear();
    Serial.print("tcp client connected from ");
    Serial.println(client.remoteIP());
  }
  if (!client) return;
  if (!client.connected()) {
    client.stop();
    Serial.println("tcp client disconnected");
    return;
  }
  while (client.available()) {
    if (readLine(client.read(), clientLine)) {
      std::string response = dispatch(clientLine) + "\n";
      client.write(reinterpret_cast<const uint8_t*>(response.data()), response.size());
      clientLine.clear();
    }
  }
}

void pollSerial() {
  while (Serial.available()) {
    if (readLine(Serial.read(), serialLine)) {
      Serial.println(dispatch(serialLine).c_str());
      serialLine.clear();
    }
  }
}

// Every 10 s, so a dropped link shows up in the serial log.
void reportStatus() {
  static uint32_t lastMs = 0;
  if (millis() - lastMs < 10000) return;
  lastMs = millis();
  Serial.print("wifi ");
  Serial.print(WiFi.status() == WL_CONNECTED ? "up" : "DOWN");
  Serial.print(", rssi ");
  Serial.print(WiFi.RSSI());
  Serial.print(" dBm, ");
  Serial.print(requests);
  Serial.println(" requests");
}

}  // namespace

void setup() {
  Serial.begin(kSerialBaud);
  while (!Serial && millis() < 3000) {
  }  // give the monitor a moment to attach so the boot log is not lost
  Serial.println("harwood0 hello " HARWOOD0_FW_VERSION);

  if (WiFi.status() == WL_NO_MODULE) {
    Serial.println("wifi module not responding; halting");
    while (true) delay(1000);
  }
  Serial.print("wifi module firmware ");
  Serial.println(WiFi.firmwareVersion());

  WiFi.setHostname("harwood0");
  Serial.print("connecting to " WIFI_SSID);
  while (WiFi.begin(WIFI_SSID, WIFI_PASSWORD) != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  while (WiFi.localIP() == IPAddress(0, 0, 0, 0)) delay(100);
  Serial.print("\nconnected, rssi ");
  Serial.print(WiFi.RSSI());
  Serial.print(" dBm, tcp://");
  Serial.print(WiFi.localIP());
  Serial.print(":");
  Serial.println(kTcpPort);

  server.begin();
}

void loop() {
  pollTcp();
  pollSerial();
  reportStatus();
}
