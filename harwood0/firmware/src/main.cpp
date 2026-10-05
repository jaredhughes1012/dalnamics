#include <Arduino.h>
#include <WiFiS3.h>

#include "config.h"
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
uint32_t lastCommandMs = 0;
bool stopped = true;

uint32_t uptimeMs() { return millis(); }

void stopActuators() {
  for (const MotorPins& m : kMotors) {
    analogWrite(m.pwm, 0);
    digitalWrite(m.in1, LOW);
    digitalWrite(m.in2, LOW);
  }
  digitalWrite(kPinDriverStby, LOW);
  for (uint8_t pin : kPinPanStepper) digitalWrite(pin, LOW);
  stopped = true;
}

const protocol::Hooks hooks{uptimeMs, stopActuators};

std::string dispatch(const std::string& request) {
  lastCommandMs = millis();
  return protocol::handle(request, hooks);
}

// Feed one received character into a line buffer, returning true when a
// complete non-empty line is ready.
bool readLine(char c, std::string& line) {
  if (c == '\n') return !line.empty();
  if (c != '\r') line += c;
  return false;
}

void pollTcp() {
  // Single controller: a new connection replaces the current one. accept()
  // (unlike available()) returns each connection once, as soon as it arrives.
  WiFiClient incoming = server.accept();
  if (incoming) {
    if (client) client.stop();
    client = incoming;
    clientLine.clear();
    Serial.println("tcp client connected");
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

void enforceCommandTimeout() {
  if (!stopped && millis() - lastCommandMs > kCommandTimeoutMs) {
    Serial.println("command timeout, stopping");
    stopActuators();
  }
}

}  // namespace

void setup() {
  Serial.begin(kSerialBaud);

  for (const MotorPins& m : kMotors) {
    pinMode(m.pwm, OUTPUT);
    pinMode(m.in1, OUTPUT);
    pinMode(m.in2, OUTPUT);
  }
  pinMode(kPinDriverStby, OUTPUT);
  for (uint8_t pin : kPinPanStepper) pinMode(pin, OUTPUT);
  stopActuators();

  WiFi.setHostname("harwood0");
  Serial.print("connecting to wifi");
  while (WiFi.begin(WIFI_SSID, WIFI_PASSWORD) != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  // WiFiS3 reports 0.0.0.0 briefly after connecting until DHCP completes.
  while (WiFi.localIP() == IPAddress(0, 0, 0, 0)) delay(100);
  Serial.print("\nconnected, tcp://");
  Serial.print(WiFi.localIP());
  Serial.print(":");
  Serial.println(kTcpPort);

  server.begin();
}

void loop() {
  pollTcp();
  pollSerial();
  enforceCommandTimeout();
}
