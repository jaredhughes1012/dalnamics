#include <motion.h>
#include <unity.h>

void setUp() {}
void tearDown() {}

void test_mecanum_forward_turns_every_wheel_forward() {
  float duty[4];
  motion::mecanumMix(0.5f, 0, 0, duty);
  for (float d : duty) TEST_ASSERT_EQUAL_FLOAT(0.5f, d);
}

void test_mecanum_strafe_left_crosses_the_wheels() {
  float duty[4];
  motion::mecanumMix(0, 1.0f, 0, duty);
  TEST_ASSERT_EQUAL_FLOAT(-1.0f, duty[0]);  // FL
  TEST_ASSERT_EQUAL_FLOAT(1.0f, duty[1]);   // FR
  TEST_ASSERT_EQUAL_FLOAT(1.0f, duty[2]);   // RL
  TEST_ASSERT_EQUAL_FLOAT(-1.0f, duty[3]);  // RR
}

void test_mecanum_turn_left_runs_the_sides_opposite() {
  float duty[4];
  motion::mecanumMix(0, 0, 0.5f, duty);
  TEST_ASSERT_TRUE(duty[0] < 0 && duty[2] < 0);  // left side backwards
  TEST_ASSERT_TRUE(duty[1] > 0 && duty[3] > 0);  // right side forwards
}

void test_mecanum_scales_down_together() {
  float duty[4];
  motion::mecanumMix(1.0f, 1.0f, 0, duty);
  TEST_ASSERT_EQUAL_FLOAT(0.0f, duty[0]);
  TEST_ASSERT_EQUAL_FLOAT(1.0f, duty[1]);
}

void test_joint_limits() {
  TEST_ASSERT_TRUE(motion::inRange(motion::kElbow, -170.0f));
  TEST_ASSERT_FALSE(motion::inRange(motion::kElbow, 1.0f));
  TEST_ASSERT_FALSE(motion::inRange(motion::kGrip, -0.5f));
  for (int j = 0; j < motion::kJointCount; j++) {
    auto joint = static_cast<motion::Joint>(j);
    TEST_ASSERT_TRUE(motion::inRange(joint, motion::kParkPose[j]));
    TEST_ASSERT_TRUE(motion::inRange(joint, motion::kJointCentre[j]));
  }
}

void test_pulse_is_centred_on_the_joint_centre() {
  TEST_ASSERT_EQUAL_FLOAT(1500.0f, motion::pulseUs(motion::kElbow, -85.0f, 1500.0f, 11.1f));
  TEST_ASSERT_EQUAL_FLOAT(1611.0f, motion::pulseUs(motion::kYaw, 10.0f, 1500.0f, 11.1f));
  TEST_ASSERT_EQUAL_FLOAT(1389.0f, motion::pulseUs(motion::kYaw, 10.0f, 1500.0f, -11.1f));
}

void test_slew_limits_each_step() {
  TEST_ASSERT_EQUAL_FLOAT(2.0f, motion::slew(0, 10, 2));
  TEST_ASSERT_EQUAL_FLOAT(-2.0f, motion::slew(0, -10, 2));
  TEST_ASSERT_EQUAL_FLOAT(1.0f, motion::slew(0, 1, 2));
}

void test_track_steps_round_trip() {
  // One pinion turn moves the carriage one pitch circumference.
  TEST_ASSERT_EQUAL(4096, motion::mmToSteps(motion::kPinionPitchCircumference));
  TEST_ASSERT_FLOAT_WITHIN(0.05f, 30.0f, motion::stepsToMm(motion::mmToSteps(30.0f)));
  TEST_ASSERT_TRUE(motion::kTrackMin > -motion::kTrackEnd);
}

int main() {
  UNITY_BEGIN();
  RUN_TEST(test_mecanum_forward_turns_every_wheel_forward);
  RUN_TEST(test_mecanum_strafe_left_crosses_the_wheels);
  RUN_TEST(test_mecanum_turn_left_runs_the_sides_opposite);
  RUN_TEST(test_mecanum_scales_down_together);
  RUN_TEST(test_joint_limits);
  RUN_TEST(test_pulse_is_centred_on_the_joint_centre);
  RUN_TEST(test_slew_limits_each_step);
  RUN_TEST(test_track_steps_round_trip);
  return UNITY_END();
}
