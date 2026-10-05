#include <Adafruit_PWMServoDriver.h>
#include <Arduino.h>
#include <WiFiS3.h>
#include <Wire.h>

#include <cmath>

#include "config.h"
#include "motion.h"
#include "protocol.h"

#if __has_include("secrets.h")
#include "secrets.h"
#else
#error "Missing include/secrets.h: copy include/secrets.example.h and set WiFi credentials"
#endif

namespace {

using motion::kJointCount;

WiFiServer server(kTcpPort);
WiFiClient client;
std::string clientLine;
std::string serialLine;
uint32_t lastCommandMs = 0;

// Drive: the current body velocity and when it expires.
protocol::Drive drive{0, 0, 0, 0};
uint32_t driveStartMs = 0;

// Arm: servos are limp until the first arm command, which starts them from the park pose.
Adafruit_PWMServoDriver servoDriver(kServoDriverAddress);
bool armEnabled = false;
float joints[kJointCount];
float jointTargets[kJointCount];
uint32_t lastServoUpdateMs = 0;

// Track: stepper position in steps from the home position (the rear end wall).
constexpr uint8_t kHalfSteps[8][4] = {{1, 0, 0, 0}, {1, 1, 0, 0}, {0, 1, 0, 0}, {0, 1, 1, 0},
                                      {0, 0, 1, 0}, {0, 0, 1, 1}, {0, 0, 0, 1}, {1, 0, 0, 1}};
bool trackHomed = false;
bool trackHoming = false;
int32_t trackSteps = 0;
int32_t trackTargetSteps = 0;
uint32_t stepIntervalUs = 0;
uint32_t lastStepUs = 0;

uint32_t uptimeMs() { return millis(); }

bool driving() { return drive.ms > 0; }
bool armMoving() {
  if (!armEnabled) return false;
  for (int j = 0; j < kJointCount; j++)
    if (joints[j] != jointTargets[j]) return true;
  return false;
}
bool trackMoving() { return trackSteps != trackTargetSteps; }

// ---- Drive

void setMotor(int i, float duty) {
  const MotorPins& m = kMotors[i];
  if (kMotorReversed[i]) duty = -duty;
  digitalWrite(m.in1, duty > 0 ? HIGH : LOW);
  digitalWrite(m.in2, duty < 0 ? HIGH : LOW);
  analogWrite(m.pwm, static_cast<int>(std::fabs(duty) * 255.0f + 0.5f));
}

void applyDrive() {
  float duty[4];
  motion::mecanumMix(drive.vx, drive.vy, drive.wz, duty);
  for (int i = 0; i < 4; i++) setMotor(i, duty[i]);
}

void stopDrive() {
  drive = protocol::Drive{0, 0, 0, 0};
  applyDrive();
}

void updateDrive() {
  if (driving() && millis() - driveStartMs >= drive.ms) stopDrive();
}

// ---- Arm

void writeServo(int j) {
  float us = motion::pulseUs(static_cast<motion::Joint>(j), joints[j], kServoCentreUs[j],
                             kServoUsPerDeg[j]);
  servoDriver.writeMicroseconds(j, static_cast<uint16_t>(us + 0.5f));
}

void updateArm() {
  if (!armEnabled || millis() - lastServoUpdateMs < kServoUpdateMs) return;
  float maxStep = kServoDegPerS * (millis() - lastServoUpdateMs) / 1000.0f;
  lastServoUpdateMs = millis();
  for (int j = 0; j < kJointCount; j++) {
    float next = motion::slew(joints[j], jointTargets[j], maxStep);
    if (next != joints[j]) {
      joints[j] = next;
      writeServo(j);
    }
  }
}

// ---- Track

void releaseStepper() {
  for (uint8_t pin : kPinTrackStepper) digitalWrite(pin, LOW);
}

void energiseStepper() {
  const uint8_t* coils = kHalfSteps[((trackSteps * kTrackDirection) % 8 + 8) % 8];
  for (int i = 0; i < 4; i++) digitalWrite(kPinTrackStepper[i], coils[i]);
}

void moveTrack(int32_t targetSteps, float stepsPerS) {
  trackTargetSteps = targetSteps;
  stepIntervalUs = static_cast<uint32_t>(1e6f / stepsPerS);
  lastStepUs = micros();
}

void updateTrack() {
  uint32_t now = micros();
  if (!trackMoving() || now - lastStepUs < stepIntervalUs) return;
  // Keep an even pace, but after a long stall (a slow WiFi poll) restart from now rather than
  // catching up in a burst the stepper cannot follow.
  lastStepUs = now - lastStepUs > 4 * stepIntervalUs ? now : lastStepUs + stepIntervalUs;
  trackSteps += trackTargetSteps > trackSteps ? 1 : -1;
  energiseStepper();
  if (trackMoving()) return;
  if (trackHoming) {
    // Against the rear wall: that is home. Back off to the travel's rear limit.
    trackHoming = false;
    trackHomed = true;
    trackSteps = motion::mmToSteps(-motion::kTrackEnd);
    moveTrack(motion::mmToSteps(motion::kTrackMin), kTrackStepsPerS);
  } else {
    releaseStepper();  // the gear train holds the carriage; save power and heat
  }
}

void stopTrack() {
  trackTargetSteps = trackSteps;
  if (trackHoming) {
    trackHoming = false;
    trackHomed = false;  // stopped part way, so the position is unknown
  }
  releaseStepper();
}

// ---- Protocol hooks

void stopActuators() {
  stopDrive();
  for (int j = 0; j < kJointCount; j++) jointTargets[j] = joints[j];  // hold where they are
  stopTrack();
}

void onDrive(const protocol::Drive& d) {
  if (d.ms == 0) {
    stopDrive();  // nothing to run for, and an ms of 0 would never expire
    return;
  }
  drive = d;
  driveStartMs = millis();
  applyDrive();
}

void onArm(const protocol::ArmTargets& targets) {
  if (!armEnabled) {
    // Unknown starting position: assume parked, and drive every servo there now.
    for (int j = 0; j < kJointCount; j++) {
      joints[j] = jointTargets[j] = motion::kParkPose[j];
      writeServo(j);
    }
    armEnabled = true;
    lastServoUpdateMs = millis();
  }
  for (int j = 0; j < kJointCount; j++)
    if (targets.set[j]) jointTargets[j] = targets.degrees[j];
}

void onTrack(float x) { moveTrack(motion::mmToSteps(x), kTrackStepsPerS); }

void onHome() {
  trackHoming = true;
  trackHomed = false;
  // Count from the front limit so the run back always reaches the rear wall.
  trackSteps = motion::mmToSteps(motion::kTrackEnd + kHomeOvertravelMm);
  moveTrack(motion::mmToSteps(-motion::kTrackEnd), kHomeStepsPerS);
}

void onState(protocol::State& s) {
  updateDrive();  // a drive that has run out since the last loop must not report as running
  s.drive = drive;
  s.drive.ms = driving() ? drive.ms - (millis() - driveStartMs) : 0;
  s.arm_enabled = armEnabled;
  for (int j = 0; j < kJointCount; j++) {
    s.joints[j] = joints[j];
    s.joint_targets[j] = jointTargets[j];
  }
  s.track_homed = trackHomed;
  s.track_homing = trackHoming;
  s.track_x = motion::stepsToMm(trackSteps);
  s.track_target = motion::stepsToMm(trackTargetSteps);
}

const protocol::Hooks hooks{uptimeMs, stopActuators, onDrive, onArm, onTrack, onHome, onState};

std::string dispatch(const std::string& request) {
  lastCommandMs = millis();
  return protocol::handle(request, hooks);
}

// ---- Transports

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
  bool moving = driving() || armMoving() || trackMoving();
  if (moving && millis() - lastCommandMs > kCommandTimeoutMs) {
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
  for (uint8_t pin : kPinTrackStepper) pinMode(pin, OUTPUT);
  for (int j = 0; j < kJointCount; j++) joints[j] = jointTargets[j] = motion::kParkPose[j];
  stopDrive();
  releaseStepper();

  Wire.begin();
  servoDriver.begin();
  servoDriver.setOscillatorFrequency(kServoOscillatorHz);
  servoDriver.setPWMFreq(kServoFrequencyHz);
  for (int j = 0; j < kJointCount; j++) servoDriver.setPin(j, 0);  // limp until commanded

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
  updateDrive();
  updateArm();
  updateTrack();
}
