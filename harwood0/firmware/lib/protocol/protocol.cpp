#include "protocol.h"

#include <ArduinoJson.h>

#include <cmath>
#include <cstring>

#ifndef HARWOOD0_FW_VERSION
#define HARWOOD0_FW_VERSION "dev"
#endif

namespace protocol {

namespace {

using motion::Joint;
using motion::kJointCount;
using motion::kJointNames;

const char* const kCommands[] = {"ping", "info", "stop", "drive", "arm", "track", "home", "state"};

// A command's outcome: nullptr on success, or an error code.
using Error = const char*;
constexpr Error kOk = nullptr;

bool isNumber(JsonVariantConst v) { return v.is<float>() && !v.is<bool>(); }

// Reads an optional number argument into `out`, keeping `out` if the key is absent.
Error number(JsonObjectConst args, const char* key, float& out) {
  JsonVariantConst v = args[key];
  if (v.isNull()) return kOk;
  if (!isNumber(v)) return "bad_args";
  out = v.as<float>();
  return std::isfinite(out) ? kOk : "bad_args";
}

// Rejects keys other than `allowed`, so a misspelt argument is never silently ignored.
Error onlyKeys(JsonObjectConst args, const char* const* allowed, size_t n) {
  for (JsonPairConst kv : args) {
    bool known = false;
    for (size_t i = 0; i < n; i++) known |= std::strcmp(kv.key().c_str(), allowed[i]) == 0;
    if (!known) return "bad_args";
  }
  return kOk;
}

void info(JsonObject result) {
  result["name"] = "harwood0";
  result["firmware"] = HARWOOD0_FW_VERSION;
  result["protocol"] = kVersion;
  JsonArray commands = result["commands"].to<JsonArray>();
  for (const char* c : kCommands) commands.add(c);
  JsonObject limits = result["limits"].to<JsonObject>();
  for (int j = 0; j < kJointCount; j++) {
    JsonArray range = limits[kJointNames[j]].to<JsonArray>();
    range.add(motion::kJointMin[j]);
    range.add(motion::kJointMax[j]);
  }
  JsonArray track = limits["track"].to<JsonArray>();
  track.add(motion::kTrackMin);
  track.add(motion::kTrackMax);
  limits["drive_ms"] = kMaxDriveMs;
}

Error drive(JsonObjectConst args, const Hooks& hooks) {
  static const char* const keys[] = {"vx", "vy", "wz", "ms"};
  if (Error e = onlyKeys(args, keys, 4)) return e;
  float v[3] = {0, 0, 0};
  float ms = kDefaultDriveMs;
  for (int i = 0; i < 3; i++) {
    if (Error e = number(args, keys[i], v[i])) return e;
    if (std::fabs(v[i]) > 1.0f) return "out_of_range";
  }
  if (Error e = number(args, "ms", ms)) return e;
  if (ms < 0 || ms > kMaxDriveMs) return "out_of_range";
  hooks.drive(Drive{v[0], v[1], v[2], static_cast<uint32_t>(ms)});
  return kOk;
}

Error arm(JsonObjectConst args, const Hooks& hooks) {
  if (Error e = onlyKeys(args, kJointNames, kJointCount)) return e;
  ArmTargets targets{};
  bool any = false;
  for (int j = 0; j < kJointCount; j++) {
    if (args[kJointNames[j]].isNull()) continue;
    float degrees = 0;
    if (Error e = number(args, kJointNames[j], degrees)) return e;
    if (!motion::inRange(static_cast<Joint>(j), degrees)) return "out_of_range";
    targets.degrees[j] = degrees;
    targets.set[j] = any = true;
  }
  if (!any) return "bad_args";
  hooks.arm(targets);
  return kOk;
}

Error track(JsonObjectConst args, const Hooks& hooks) {
  static const char* const keys[] = {"x"};
  if (Error e = onlyKeys(args, keys, 1)) return e;
  float x = NAN;
  if (Error e = number(args, "x", x)) return e;
  if (std::isnan(x)) return "bad_args";
  if (x < motion::kTrackMin || x > motion::kTrackMax) return "out_of_range";
  State state{};
  hooks.state(state);
  if (state.track_homing) return "busy";
  if (!state.track_homed) return "not_homed";
  hooks.track(x);
  return kOk;
}

void joints(JsonObject out, const float* degrees) {
  for (int j = 0; j < kJointCount; j++) out[kJointNames[j]] = degrees[j];
}

void state(JsonObject result, const Hooks& hooks) {
  State s{};
  hooks.state(s);
  JsonObject drive = result["drive"].to<JsonObject>();
  drive["vx"] = s.drive.vx;
  drive["vy"] = s.drive.vy;
  drive["wz"] = s.drive.wz;
  drive["ms_left"] = s.drive.ms;
  JsonObject arm = result["arm"].to<JsonObject>();
  arm["enabled"] = s.arm_enabled;
  joints(arm["joints"].to<JsonObject>(), s.joints);
  joints(arm["targets"].to<JsonObject>(), s.joint_targets);
  JsonObject track = result["track"].to<JsonObject>();
  track["homed"] = s.track_homed;
  track["homing"] = s.track_homing;
  if (s.track_homed) {
    track["x"] = s.track_x;
    track["target"] = s.track_target;
  } else {
    track["x"] = nullptr;
    track["target"] = nullptr;
  }
}

}  // namespace

std::string handle(const std::string& request, const Hooks& hooks) {
  JsonDocument req;
  JsonDocument res;

  if (deserializeJson(req, request) || !req.is<JsonObject>()) {
    res["id"] = nullptr;
    res["ok"] = false;
    res["error"] = "bad_json";
  } else {
    res["id"] = req["id"];
    res["ok"] = true;
    std::string cmd = req["cmd"] | "";
    JsonVariantConst raw = req["args"];
    JsonObjectConst args = raw.as<JsonObjectConst>();
    Error error = kOk;

    if (!raw.isNull() && !raw.is<JsonObjectConst>()) {
      error = "bad_args";
    } else if (cmd == "ping") {
      res["result"]["uptime_ms"] = hooks.uptime_ms();
    } else if (cmd == "info") {
      info(res["result"].to<JsonObject>());
    } else if (cmd == "stop") {
      hooks.stop();
    } else if (cmd == "drive") {
      error = drive(args, hooks);
    } else if (cmd == "arm") {
      error = arm(args, hooks);
    } else if (cmd == "track") {
      error = track(args, hooks);
    } else if (cmd == "home") {
      hooks.home();
    } else if (cmd == "state") {
      state(res["result"].to<JsonObject>(), hooks);
    } else {
      error = "unknown_command";
    }

    if (error) {
      res.remove("result");
      res["ok"] = false;
      res["error"] = error;
    }
  }

  std::string out;
  serializeJson(res, out);
  return out;
}

}  // namespace protocol
