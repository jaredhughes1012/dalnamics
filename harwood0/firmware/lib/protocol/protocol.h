// Command protocol shared by every transport (serial, TCP).
// Pure C++ with no Arduino dependencies so it can be unit-tested on the host.
// See docs/protocol.md for the wire format.
#pragma once

#include <cstdint>
#include <string>

namespace protocol {

constexpr int kVersion = 0;

// Hardware operations the protocol dispatches to. Firmware wires these to real
// peripherals; tests wire them to fakes.
struct Hooks {
  uint32_t (*uptime_ms)();
  void (*stop)();
};

// Handle one JSON request and return the JSON response.
std::string handle(const std::string& request, const Hooks& hooks);

}  // namespace protocol
