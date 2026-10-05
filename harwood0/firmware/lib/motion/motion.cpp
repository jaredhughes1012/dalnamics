#include "motion.h"

#include <cmath>

namespace motion {

const char* const kJointNames[kJointCount] = {"yaw", "shoulder", "elbow", "grip"};

bool inRange(Joint joint, float degrees) {
  return std::isfinite(degrees) && degrees >= kJointMin[joint] && degrees <= kJointMax[joint];
}

float pulseUs(Joint joint, float degrees, float centre_us, float us_per_deg) {
  return centre_us + (degrees - kJointCentre[joint]) * us_per_deg;
}

float slew(float current, float target, float max_step) {
  if (target > current + max_step) return current + max_step;
  if (target < current - max_step) return current - max_step;
  return target;
}

void mecanumMix(float vx, float vy, float wz, float duty[4]) {
  // Rollers in an X: strafing left turns the front-left and rear-right wheels backwards.
  duty[0] = vx - vy - wz;
  duty[1] = vx + vy + wz;
  duty[2] = vx + vy - wz;
  duty[3] = vx - vy + wz;
  float peak = 1.0f;
  for (int i = 0; i < 4; i++) peak = std::fmax(peak, std::fabs(duty[i]));
  for (int i = 0; i < 4; i++) duty[i] /= peak;
}

int32_t mmToSteps(float mm) { return static_cast<int32_t>(std::lround(mm * kStepsPerMm)); }

float stepsToMm(int32_t steps) { return static_cast<float>(steps) / kStepsPerMm; }

}  // namespace motion
