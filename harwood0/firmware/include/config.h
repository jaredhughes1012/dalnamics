#pragma once

#include <Arduino.h>

#include <cstdint>

#include "motion.h"

constexpr uint16_t kTcpPort = 7777;
constexpr uint32_t kSerialBaud = 115200;

// Actuators stop if no command arrives within this window, so a dropped
// connection or crashed controller can never leave the robot moving.
constexpr uint32_t kCommandTimeoutMs = 1000;

// Pin map (docs/hardware.md#pin-map). Two TB6612FNG boards: "front" drives FL (channel A)
// and FR (B), "rear" drives RL (A) and RR (B). Each board's STBY is wired to its own VCC.
// A4/A5 are the I2C bus to the servo driver. D0/D1 (Serial1) are left free for a future
// onboard computer UART link.
struct MotorPins {
  uint8_t pwm;
  uint8_t in1;
  uint8_t in2;
};

constexpr MotorPins kMotorFL{D3, D2, D4};
constexpr MotorPins kMotorFR{D5, D7, D8};
constexpr MotorPins kMotorRL{D6, D12, D13};
constexpr MotorPins kMotorRR{D9, A0, A1};
constexpr MotorPins kMotors[] = {kMotorFL, kMotorFR, kMotorRL, kMotorRR};

// The motors on each side face opposite ways, so one side runs reversed. If a wheel turns
// the wrong way, flip its entry here (or swap its two motor leads).
constexpr bool kMotorReversed[] = {false, true, false, true};

// Track stepper (28BYJ-48 via ULN2003) coil inputs IN1-IN4.
constexpr uint8_t kPinTrackStepper[] = {A2, A3, D10, D11};

// +1 if positive steps move the carriage forward (towards the nose), else -1.
constexpr int8_t kTrackDirection = 1;
constexpr float kTrackStepsPerS = 600.0f;  // about 12 mm/s
constexpr float kHomeStepsPerS = 400.0f;
// Homing runs the carriage back into the rear end wall, further than the full travel, so it
// always ends against the wall; the stepper slips harmlessly while it is stalled there.
constexpr float kHomeOvertravelMm = 15.0f;

// Servo driver (PCA9685) on I2C, at its default address. Channels follow motion::Joint
// (yaw 0, shoulder 1, elbow 2, grip 3); channel 4 only powers the arm camera.
constexpr uint8_t kServoDriverAddress = 0x40;
constexpr float kServoFrequencyHz = 50.0f;
// Nominal; each board's oscillator runs a few percent off, which the per-servo calibration
// below absorbs (docs/hardware.md#servo-calibration).
constexpr uint32_t kServoOscillatorHz = 25000000;

// Pulse at each joint's centre (motion::kJointCentre), and how it changes per degree.
// Negative us/deg if the servo's mounting turns the joint the other way. Tune these per
// servo during calibration.
constexpr float kServoCentreUs[motion::kJointCount] = {1500.0f, 1500.0f, 1500.0f, 1500.0f};
constexpr float kServoUsPerDeg[motion::kJointCount] = {11.1f, 11.1f, 11.1f, 11.1f};
constexpr float kServoDegPerS = 60.0f;  // how fast every joint moves to its target
constexpr uint32_t kServoUpdateMs = 20;  // once per servo frame
