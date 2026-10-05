// Motion maths shared by the protocol and the firmware: joint limits, servo pulse
// mapping, mecanum mixing, and track step conversions.
// Pure C++ with no Arduino dependencies so it can be unit-tested on the host.
//
// Angles and the carriage position use the CAD's conventions (cad/src/harwood0_cad/arm.py),
// and the limits mirror its ranges; cad/tests/test_firmware_limits.py checks they agree.
#pragma once

#include <cstddef>
#include <cstdint>

namespace motion {

// Arm joints, in PCA9685 channel order.
enum Joint : uint8_t { kYaw, kShoulder, kElbow, kGrip, kJointCount };

extern const char* const kJointNames[kJointCount];

// Joint ranges (degrees). yaw: 0 points the arm across the table, -90 forward.
// shoulder: elevation above horizontal. elbow: bend relative to the upper arm, negative
// down. grip: the gripper gear's turn, 0 closed.
constexpr float kJointMin[kJointCount] = {-90.0f, -90.0f, -170.0f, 0.0f};
constexpr float kJointMax[kJointCount] = {90.0f, 90.0f, 0.0f, 90.0f};

// Joint angle at each servo's centre pulse: the middle of its range, where its horn is fitted.
constexpr float kJointCentre[kJointCount] = {0.0f, 0.0f, -85.0f, 45.0f};

// Where the firmware assumes the arm is at power-up (the CAD's "park" pose). The first
// arm command starts each servo here, so leave the arm parked before switching off.
constexpr float kParkPose[kJointCount] = {0.0f, 45.0f, -130.0f, 0.0f};

// Carriage travel (mm, carriage centre along the body's X axis). The slot's end walls stop
// the carriage at +/-kTrackEnd; commands stay kTrackMargin inside them.
constexpr float kTrackEnd = 67.0f;
constexpr float kTrackMargin = 2.0f;
constexpr float kTrackMin = -kTrackEnd + kTrackMargin;
constexpr float kTrackMax = kTrackEnd - kTrackMargin;

// Track drive: 28BYJ-48 half-stepping, 18-tooth module 1.5 pinion on the rack.
constexpr float kStepsPerRev = 4096.0f;
constexpr float kPinionPitchCircumference = 3.14159265f * 1.5f * 18.0f;
constexpr float kStepsPerMm = kStepsPerRev / kPinionPitchCircumference;

bool inRange(Joint joint, float degrees);

// Servo pulse for a joint angle. `us_per_deg` is negative for a servo mounted so that
// increasing pulse turns the joint the negative way.
float pulseUs(Joint joint, float degrees, float centre_us, float us_per_deg);

// Move `current` towards `target` by at most `max_step`, returning the new value.
float slew(float current, float target, float max_step);

// Wheel duties in [-1, 1] for a body velocity, each component a fraction of full speed:
// vx forward, vy left, wz anticlockwise seen from above. Order: FL, FR, RL, RR.
// Scaled down together if any wheel would exceed full speed.
void mecanumMix(float vx, float vy, float wz, float duty[4]);

int32_t mmToSteps(float mm);
float stepsToMm(int32_t steps);

}  // namespace motion
