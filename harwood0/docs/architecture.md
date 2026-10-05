# Architecture

```
┌──────────────────┐  HTTP (later: agent tools)  ┌──────────────────┐  TCP / serial, JSON lines  ┌──────────────────┐
│ Agent controller │ ──────────────────────────▶ │ api/ (Python)    │ ─────────────────────────▶ │ firmware/        │
│ / developer      │                             │ capability layer │                            │ Uno R4 WiFi      │
└──────────────────┘                             └──────────────────┘                            └──────────────────┘
                                                   runs on a laptop,  ◀──── video over WiFi ────   2× ESP32-CAM
                                                   or an SBC on board                               (nose, gripper)
```

The robot's physical design, parts list, and wiring are in [hardware.md](hardware.md).

## Layers

**Firmware** runs on the Uno R4 WiFi and owns everything timing-critical: the four mecanum drive motors, the track stepper, the arm's servos (through a PCA9685 servo driver on I2C), and safety. It exposes a small set of commands over the [protocol](protocol.md) and makes no high-level decisions. It enforces joint and track limits, moves each servo at a limited speed, and homes the carriage against the track's end wall. If commands stop arriving within the command timeout, it stops the wheels and carriage and holds the arm where it is, so a dropped WiFi link or a crashed controller can never leave the robot moving. Drive commands also expire on their own.

**Cameras** are two ESP32-CAMs: one fixed in the nose, one on the gripper looking between the fingers. Each joins the same WiFi network and streams video directly to the API, bypassing the motion controller. The arm camera's pose follows from the carriage position and joint angles in the firmware's `state`, through the same kinematics as the CAD (`cad/src/harwood0_cad/arm.py`), so each frame can be paired with where the camera was.

**API** turns protocol commands into typed capabilities (`harwood0_api.robot.Robot`). Each capability is defined once, and its docstring and Pydantic types describe it. The HTTP routes are thin adapters over these methods, and agent tool interfaces (such as an MCP server) wrap the same methods. The API also consumes the camera stream for depth estimation, object detection, and 3D reconstruction. The transport is swappable:

- `TcpTransport` talks to the firmware over WiFi, and pings it on a heartbeat while connected so motions that outlast a request keep running.
- `SimTransport` simulates the firmware in process, with the same validation, limits, and timing, for development and tests without hardware.

The API has no dependency on where it runs. On a laptop it reaches the robot over WiFi. On a single-board computer mounted on the robot it can use the same TCP transport, or a serial transport over the Uno's spare UART; the firmware serves the same protocol on both.

**CAD** is a Python package that keeps printed parts and purchased-part models separate. Every printed part is sized and placed from the hardware dimensions and the layout modules. The arm's kinematics, joint limits, and cable runs live there too, and the firmware's limits are checked against them. Tests check the parts are valid and printable, that nothing in the assembly interferes in any named pose, that the robot does not tip, and that every cable has room. See [hardware.md](hardware.md#cad-workflow).

## Tool choices

| Concern | Choice | Why |
|---|---|---|
| CAD | build123d | Code-first B-rep modelling on the OpenCascade kernel: true fillets and chamfers, STEP export for other CAD tools, STL export for slicing, and boolean operations for interference checks. It is Python, so parts share tooling and tests with the API. |
| CAD renders | PyVista (VTK), offscreen | Deterministic multi-view PNGs from the command line, so every change can be checked visually without opening a viewer. `harwood0-show` sends the same targets to OCP CAD Viewer in VS Code for interactive inspection. |
| Motion controller | Arduino Uno R4 WiFi | Built-in WiFi (an ESP32-S3 co-processor), 5 V-tolerant I/O, and enough pins for four motors and a stepper, with I2C for the servo driver. Already on hand. |
| Servo driver | PCA9685 | Sixteen hardware-timed servo channels over two I2C pins, so the arm's servos cost no Uno pins or timers, and it mounts in the tower where the servo leads end. |
| Firmware framework | Arduino on PlatformIO | The Arduino API and library ecosystem cover the motor drivers and servo. PlatformIO adds pinned dependencies in `platformio.ini`, multiple build targets, and host-side unit tests. |
| Camera | ESP32-CAM | A self-contained WiFi camera, so video never passes through the motion controller. Already on hand. |
| API | Python + FastAPI | Python has the strongest robotics and vision ecosystem (OpenCV, PyTorch depth and detection models, Open3D) and a first-class MCP SDK for agent tooling. FastAPI generates an OpenAPI description of every capability. |
| Firmware ↔ API link | Newline-delimited JSON over TCP (WiFi) and serial | The same framing on every transport, human-readable, and debuggable with `nc`. No broker or extra infrastructure. |

## Testing

- `cad/tests`: geometry validity, build-volume checks, key features, assembly interference and tipping in every named arm pose, reach, cable clearance over a sweep of poses, and agreement with the firmware's limits.
- `firmware/test`: protocol and motion logic compiled and run on the host (`pio test -e native`). The protocol (`lib/protocol`) and the motion maths (`lib/motion`: limits, mecanum mixing, servo pulses, track steps) have no Arduino dependencies, so they can be tested without hardware.
- `api/tests`: HTTP routes against the simulator with an injected clock, the simulator's validation, and the TCP transport and heartbeat against a local fake firmware server.
