#include <ArduinoJson.h>
#include <protocol.h>
#include <unity.h>

namespace {

int stopCalls = 0;
int homeCalls = 0;
protocol::Drive lastDrive{};
protocol::ArmTargets lastArm{};
int armCalls = 0;
float lastTrack = 0;
int trackCalls = 0;
protocol::State fakeState{};

uint32_t fakeUptime() { return 1234; }
void fakeStop() { stopCalls++; }
void fakeDrive(const protocol::Drive& d) { lastDrive = d; }
void fakeArm(const protocol::ArmTargets& t) {
  lastArm = t;
  armCalls++;
}
void fakeTrack(float x) {
  lastTrack = x;
  trackCalls++;
}
void fakeHome() { homeCalls++; }
void fakeStateHook(protocol::State& s) { s = fakeState; }

const protocol::Hooks hooks{fakeUptime, fakeStop, fakeDrive, fakeArm,
                            fakeTrack,  fakeHome, fakeStateHook};

JsonDocument call(const char* request) {
  JsonDocument res;
  deserializeJson(res, protocol::handle(request, hooks));
  return res;
}

void assertError(const char* request, const char* code) {
  JsonDocument res = call(request);
  TEST_ASSERT_FALSE(res["ok"].as<bool>());
  TEST_ASSERT_EQUAL_STRING(code, res["error"]);
}

}  // namespace

void setUp() {
  stopCalls = homeCalls = armCalls = trackCalls = 0;
  lastDrive = {};
  lastArm = {};
  fakeState = {};
}
void tearDown() {}

void test_ping_returns_uptime_and_echoes_id() {
  JsonDocument res = call(R"({"id":7,"cmd":"ping"})");
  TEST_ASSERT_EQUAL(7, res["id"].as<int>());
  TEST_ASSERT_TRUE(res["ok"].as<bool>());
  TEST_ASSERT_EQUAL(1234, res["result"]["uptime_ms"].as<uint32_t>());
}

void test_info_lists_commands_and_limits() {
  JsonDocument res = call(R"({"id":1,"cmd":"info"})");
  TEST_ASSERT_EQUAL_STRING("harwood0", res["result"]["name"]);
  TEST_ASSERT_EQUAL(protocol::kVersion, res["result"]["protocol"].as<int>());
  TEST_ASSERT_EQUAL(8, res["result"]["commands"].size());
  TEST_ASSERT_EQUAL_FLOAT(-140.0f, res["result"]["limits"]["elbow"][0].as<float>());
  TEST_ASSERT_EQUAL_FLOAT(65.0f, res["result"]["limits"]["track"][1].as<float>());
}

void test_stop_calls_hook() {
  JsonDocument res = call(R"({"id":2,"cmd":"stop"})");
  TEST_ASSERT_TRUE(res["ok"].as<bool>());
  TEST_ASSERT_EQUAL(1, stopCalls);
}

void test_drive_passes_velocity_and_defaults() {
  JsonDocument res = call(R"({"id":1,"cmd":"drive","args":{"vx":0.5,"wz":-0.25}})");
  TEST_ASSERT_TRUE(res["ok"].as<bool>());
  TEST_ASSERT_EQUAL_FLOAT(0.5f, lastDrive.vx);
  TEST_ASSERT_EQUAL_FLOAT(0.0f, lastDrive.vy);
  TEST_ASSERT_EQUAL_FLOAT(-0.25f, lastDrive.wz);
  TEST_ASSERT_EQUAL(protocol::kDefaultDriveMs, lastDrive.ms);
}

void test_drive_rejects_bad_args() {
  assertError(R"({"id":1,"cmd":"drive","args":{"vx":1.5}})", "out_of_range");
  assertError(R"({"id":1,"cmd":"drive","args":{"vx":0.1,"ms":60000}})", "out_of_range");
  assertError(R"({"id":1,"cmd":"drive","args":{"vx":"fast"}})", "bad_args");
  assertError(R"({"id":1,"cmd":"drive","args":{"speed":0.2}})", "bad_args");
  assertError(R"({"id":1,"cmd":"drive","args":[1]})", "bad_args");
}

void test_arm_sets_only_given_joints() {
  JsonDocument res = call(R"({"id":1,"cmd":"arm","args":{"shoulder":30,"grip":10}})");
  TEST_ASSERT_TRUE(res["ok"].as<bool>());
  TEST_ASSERT_EQUAL(1, armCalls);
  TEST_ASSERT_FALSE(lastArm.set[motion::kYaw]);
  TEST_ASSERT_TRUE(lastArm.set[motion::kShoulder]);
  TEST_ASSERT_EQUAL_FLOAT(30.0f, lastArm.degrees[motion::kShoulder]);
  TEST_ASSERT_TRUE(lastArm.set[motion::kGrip]);
}

void test_arm_rejects_out_of_range_without_moving() {
  assertError(R"({"id":1,"cmd":"arm","args":{"shoulder":30,"elbow":10}})", "out_of_range");
  assertError(R"({"id":1,"cmd":"arm","args":{}})", "bad_args");
  assertError(R"({"id":1,"cmd":"arm","args":{"wrist":5}})", "bad_args");
  TEST_ASSERT_EQUAL(0, armCalls);
}

void test_track_requires_homing() {
  assertError(R"({"id":1,"cmd":"track","args":{"x":10}})", "not_homed");
  fakeState.track_homing = true;
  assertError(R"({"id":1,"cmd":"track","args":{"x":10}})", "busy");
  fakeState = {};
  fakeState.track_homed = true;
  JsonDocument res = call(R"({"id":1,"cmd":"track","args":{"x":10}})");
  TEST_ASSERT_TRUE(res["ok"].as<bool>());
  TEST_ASSERT_EQUAL_FLOAT(10.0f, lastTrack);
  assertError(R"({"id":1,"cmd":"track","args":{"x":66}})", "out_of_range");
  assertError(R"({"id":1,"cmd":"track"})", "bad_args");
  TEST_ASSERT_EQUAL(1, trackCalls);
}

void test_home_calls_hook() {
  TEST_ASSERT_TRUE(call(R"({"id":1,"cmd":"home"})")["ok"].as<bool>());
  TEST_ASSERT_EQUAL(1, homeCalls);
}

void test_state_reports_everything() {
  fakeState.drive = {0.2f, 0, 0, 300};
  fakeState.arm_enabled = true;
  fakeState.joints[motion::kElbow] = -90.0f;
  fakeState.joint_targets[motion::kElbow] = -100.0f;
  JsonDocument res = call(R"({"id":1,"cmd":"state"})");
  JsonObject result = res["result"];
  TEST_ASSERT_EQUAL_FLOAT(0.2f, result["drive"]["vx"].as<float>());
  TEST_ASSERT_EQUAL(300, result["drive"]["ms_left"].as<int>());
  TEST_ASSERT_TRUE(result["arm"]["enabled"].as<bool>());
  TEST_ASSERT_EQUAL_FLOAT(-90.0f, result["arm"]["joints"]["elbow"].as<float>());
  TEST_ASSERT_EQUAL_FLOAT(-100.0f, result["arm"]["targets"]["elbow"].as<float>());
  TEST_ASSERT_FALSE(result["track"]["homed"].as<bool>());
  TEST_ASSERT_TRUE(result["track"]["x"].isNull());
}

void test_unknown_command() {
  JsonDocument res = call(R"({"id":3,"cmd":"fly"})");
  TEST_ASSERT_FALSE(res["ok"].as<bool>());
  TEST_ASSERT_EQUAL_STRING("unknown_command", res["error"]);
}

void test_bad_json() {
  JsonDocument res = call("not json");
  TEST_ASSERT_FALSE(res["ok"].as<bool>());
  TEST_ASSERT_TRUE(res["id"].isNull());
  TEST_ASSERT_EQUAL_STRING("bad_json", res["error"]);
}

int main() {
  UNITY_BEGIN();
  RUN_TEST(test_ping_returns_uptime_and_echoes_id);
  RUN_TEST(test_info_lists_commands_and_limits);
  RUN_TEST(test_stop_calls_hook);
  RUN_TEST(test_drive_passes_velocity_and_defaults);
  RUN_TEST(test_drive_rejects_bad_args);
  RUN_TEST(test_arm_sets_only_given_joints);
  RUN_TEST(test_arm_rejects_out_of_range_without_moving);
  RUN_TEST(test_track_requires_homing);
  RUN_TEST(test_home_calls_hook);
  RUN_TEST(test_state_reports_everything);
  RUN_TEST(test_unknown_command);
  RUN_TEST(test_bad_json);
  return UNITY_END();
}
