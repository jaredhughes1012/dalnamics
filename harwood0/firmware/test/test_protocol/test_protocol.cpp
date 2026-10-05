#include <ArduinoJson.h>
#include <protocol.h>
#include <unity.h>

namespace {

int stopCalls = 0;
uint32_t fakeUptime() { return 1234; }
void fakeStop() { stopCalls++; }
const protocol::Hooks hooks{fakeUptime, fakeStop};

JsonDocument call(const char* request) {
  JsonDocument res;
  deserializeJson(res, protocol::handle(request, hooks));
  return res;
}

}  // namespace

void setUp() { stopCalls = 0; }
void tearDown() {}

void test_ping_returns_uptime_and_echoes_id() {
  JsonDocument res = call(R"({"id":7,"cmd":"ping"})");
  TEST_ASSERT_EQUAL(7, res["id"].as<int>());
  TEST_ASSERT_TRUE(res["ok"].as<bool>());
  TEST_ASSERT_EQUAL(1234, res["result"]["uptime_ms"].as<uint32_t>());
}

void test_info_lists_commands() {
  JsonDocument res = call(R"({"id":1,"cmd":"info"})");
  TEST_ASSERT_EQUAL_STRING("harwood0", res["result"]["name"]);
  TEST_ASSERT_EQUAL(protocol::kVersion, res["result"]["protocol"].as<int>());
  TEST_ASSERT_EQUAL(3, res["result"]["commands"].size());
}

void test_stop_calls_hook() {
  JsonDocument res = call(R"({"id":2,"cmd":"stop"})");
  TEST_ASSERT_TRUE(res["ok"].as<bool>());
  TEST_ASSERT_EQUAL(1, stopCalls);
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
  RUN_TEST(test_info_lists_commands);
  RUN_TEST(test_stop_calls_hook);
  RUN_TEST(test_unknown_command);
  RUN_TEST(test_bad_json);
  return UNITY_END();
}
