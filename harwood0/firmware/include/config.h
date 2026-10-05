#pragma once

#include <Arduino.h>

#include <cstdint>

constexpr uint16_t kTcpPort = 7777;
constexpr uint32_t kSerialBaud = 115200;

// Actuators stop if no command arrives within this window, so a dropped
// connection or crashed controller can never leave the robot moving.
constexpr uint32_t kCommandTimeoutMs = 1000;

// Pin map. Two TB6612FNG boards: "front" drives FL (channel A) and FR (B),
// "rear" drives RL (A) and RR (B). Both boards share one STBY pin.
// D0/D1 (Serial1) are left free for a future onboard computer UART link.
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

constexpr uint8_t kPinDriverStby = A2;

// Pan stepper (28BYJ-48 via ULN2003) coil inputs IN1-IN4.
constexpr uint8_t kPinPanStepper[] = {A3, A4, A5, D11};

// Tilt servo (MG90S) signal.
constexpr uint8_t kPinTiltServo = D10;
