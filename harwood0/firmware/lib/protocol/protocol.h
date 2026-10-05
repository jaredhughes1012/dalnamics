// Command protocol shared by every transport (serial, TCP).
// Pure C++ with no Arduino dependencies so it can be unit-tested on the host.
// See docs/protocol.md for the wire format.
#pragma once

#include <cstdint>
#include <string>

#include "motion.h"

namespace protocol {

constexpr int kVersion = 1;

// Longest a single drive command may run before the wheels stop on their own.
constexpr uint32_t kMaxDriveMs = 5000;
constexpr uint32_t kDefaultDriveMs = 500;

struct Drive {
  float vx;
  float vy;
  float wz;
  uint32_t ms;
};

struct ArmTargets {
  float degrees[motion::kJointCount];
  bool set[motion::kJointCount];  // joints left out of the command keep their target
};

struct State {
  Drive drive;  // ms is the time left
  bool arm_enabled;  // false until the first arm command; the servos are limp until then
  float joints[motion::kJointCount];
  float joint_targets[motion::kJointCount];
  bool track_homed;
  bool track_homing;
  float track_x;  // valid once homed
  float track_target;
};

// Hardware operations the protocol dispatches to, after validating arguments. Firmware
// wires these to real peripherals; tests wire them to fakes.
struct Hooks {
  uint32_t (*uptime_ms)();
  void (*stop)();
  void (*drive)(const Drive&);
  void (*arm)(const ArmTargets&);
  void (*track)(float x);
  void (*home)();
  void (*state)(State&);
};

// Handle one JSON request and return the JSON response.
std::string handle(const std::string& request, const Hooks& hooks);

}  // namespace protocol
