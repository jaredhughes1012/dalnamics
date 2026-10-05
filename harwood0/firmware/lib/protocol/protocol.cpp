#include "protocol.h"

#include <ArduinoJson.h>

#ifndef HARWOOD0_FW_VERSION
#define HARWOOD0_FW_VERSION "dev"
#endif

namespace protocol {

namespace {

const char* const kCommands[] = {"ping", "info", "stop"};

void error(JsonDocument& res, const char* code) {
  res["ok"] = false;
  res["error"] = code;
}

}  // namespace

std::string handle(const std::string& request, const Hooks& hooks) {
  JsonDocument req;
  JsonDocument res;

  if (deserializeJson(req, request)) {
    res["id"] = nullptr;
    error(res, "bad_json");
  } else {
    res["id"] = req["id"];
    std::string cmd = req["cmd"] | "";

    if (cmd == "ping") {
      res["ok"] = true;
      res["result"]["uptime_ms"] = hooks.uptime_ms();
    } else if (cmd == "info") {
      res["ok"] = true;
      JsonObject result = res["result"].to<JsonObject>();
      result["name"] = "harwood0";
      result["firmware"] = HARWOOD0_FW_VERSION;
      result["protocol"] = kVersion;
      JsonArray commands = result["commands"].to<JsonArray>();
      for (const char* c : kCommands) commands.add(c);
    } else if (cmd == "stop") {
      hooks.stop();
      res["ok"] = true;
    } else {
      error(res, "unknown_command");
    }
  }

  std::string out;
  serializeJson(res, out);
  return out;
}

}  // namespace protocol
