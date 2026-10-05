# Architecture

```
┌──────────────────┐  HTTP (later: agent tools)  ┌──────────────────┐  TCP / serial, JSON lines  ┌──────────────────┐
│ Agent controller │ ──────────────────────────▶ │ api/ (Python)    │ ─────────────────────────▶ │ firmware/        │
│ / developer      │                             │ capability layer │                            │ Uno R4 WiFi      │
└──────────────────┘                             └──────────────────┘                            └──────────────────┘
                                                   runs on a laptop,  ◀──── video over WiFi ────   ESP32-CAM
                                                   or an SBC on board                               (camera head)
```

The robot's physical design, parts list, and wiring are in [hardware.md](hardware.md).

## Layers

**Firmware** runs on the Uno R4 WiFi and owns everything timing-critical: the four mecanum drive motors, the pan stepper, the tilt servo, and safety. It exposes a small set of commands over the [protocol](protocol.md) and makes no high-level decisions. If commands stop arriving within the command timeout, it stops all actuators, so a dropped WiFi link or a crashed controller can never leave the robot moving.

**Camera** is an ESP32-CAM on the pan/tilt head. It joins the same WiFi network and streams video directly to the API, bypassing the motion controller. The pan and tilt angles come from the firmware (the stepper's step count and the servo's commanded position), so each frame can be paired with the camera's pose on the robot.

**API** turns protocol commands into typed capabilities (`harwood0_api.robot.Robot`). Each capability is defined once, and its docstring and Pydantic types describe it. The HTTP routes are thin adapters over these methods, and agent tool interfaces (such as an MCP server) wrap the same methods. The API also consumes the camera stream for depth estimation, object detection, and 3D reconstruction. The transport is swappable:

- `TcpTransport` talks to the firmware over WiFi.
- `SimTransport` is an in-process stand-in for the firmware, used for development and tests without hardware.

The API has no dependency on where it runs. On a laptop it reaches the robot over WiFi. On a single-board computer mounted on the robot it can use the same TCP transport, or a serial transport over the Uno's spare UART; the firmware serves the same protocol on both.

**CAD** is a Python package that keeps printed parts and purchased-part models separate. Every printed part is sized and placed from the hardware dimensions and `params.py`. Tests check the parts are valid and printable and that nothing in the assembly interferes. See [hardware.md](hardware.md#cad-workflow).

## Tool choices

| Concern | Choice | Why |
|---|---|---|
| CAD | build123d | Code-first B-rep modelling on the OpenCascade kernel: true fillets and chamfers, STEP export for other CAD tools, STL export for slicing, and boolean operations for interference checks. It is Python, so parts share tooling and tests with the API. |
| CAD renders | PyVista (VTK), offscreen | Deterministic multi-view PNGs from the command line, so every change can be checked visually without opening a viewer. `harwood0-show` sends the same targets to OCP CAD Viewer in VS Code for interactive inspection. |
| Motion controller | Arduino Uno R4 WiFi | Built-in WiFi (an ESP32-S3 co-processor), 5 V-tolerant I/O, and enough pins for four motors, a stepper, and a servo. Already on hand. |
| Firmware framework | Arduino on PlatformIO | The Arduino API and library ecosystem cover the motor drivers and servo. PlatformIO adds pinned dependencies in `platformio.ini`, multiple build targets, and host-side unit tests. |
| Camera | ESP32-CAM | A self-contained WiFi camera, so video never passes through the motion controller. Already on hand. |
| API | Python + FastAPI | Python has the strongest robotics and vision ecosystem (OpenCV, PyTorch depth and detection models, Open3D) and a first-class MCP SDK for agent tooling. FastAPI generates an OpenAPI description of every capability. |
| Firmware ↔ API link | Newline-delimited JSON over TCP (WiFi) and serial | The same framing on every transport, human-readable, and debuggable with `nc`. No broker or extra infrastructure. |

## Testing

- `cad/tests`: geometry validity, build-volume checks, and assembly interference at several camera poses.
- `firmware/test`: protocol logic compiled and run on the host (`pio test -e native`). The protocol lives in `lib/protocol` with no Arduino dependencies so it can be tested without hardware.
- `api/tests`: HTTP routes against the simulator, and the TCP transport against a local fake firmware server.
