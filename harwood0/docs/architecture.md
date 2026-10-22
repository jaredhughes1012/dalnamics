# Architecture

```
┌──────────────────┐  HTTP (later: agent tools)  ┌──────────────────┐  TCP / serial, JSON lines  ┌──────────────────┐
│ Agent controller │ ──────────────────────────▶ │ api/ (Python)    │ ─────────────────────────▶ │ firmware/        │
│ / developer      │                             │ capability layer │                            │ Uno R4 WiFi      │
└──────────────────┘                             └──────────────────┘                            └──────────────────┘
                                                   │  runs on a laptop,  ◀──── video over WiFi ────   2× ESP32-CAM
                                                   │  or an SBC on board                               (nose, gripper)
                                                   │ MQTT (optional)
                                                   ▼
                                                 ┌──────────────────┐
                                                 │ dalnamics        │
                                                 │ Mosquitto ↔      │
                                                 │ devicemgr        │
                                                 └──────────────────┘
```

The robot's physical design, parts list, and wiring are in [hardware.md](hardware.md).

## Layers

**Firmware** runs on the Uno R4 WiFi and owns everything timing-critical: the four mecanum drive motors, the track stepper, the arm's servos (through a PCA9685 servo driver on I2C), and safety. It exposes a small set of commands over the [protocol](protocol.md) and makes no high-level decisions. It enforces joint and track limits, moves each servo at a limited speed, and homes the carriage against the track's end wall. If commands stop arriving within the command timeout, it stops the wheels and carriage and holds the arm where it is, so a dropped WiFi link or a crashed controller can never leave the robot moving. Drive commands also expire on their own.

**Cameras** are two ESP32-CAMs: one fixed in the nose, one on the gripper looking between the fingers. Each runs the same firmware (`camera/`), joins the same WiFi network as `harwood0-nose.local` or `harwood0-arm.local`, and streams MJPEG directly to the API, bypassing the motion controller. An ESP32-CAM serves one stream at a time, so the API holds the only connection to each camera (`harwood0_api.camera.Camera`) and shares its latest frame with every consumer: the viewer, `/cameras/{name}/frame`, and vision. The arm camera's pose follows from the carriage position and joint angles in the firmware's `state`, through the same kinematics as the CAD (`cad/src/harwood0_cad/arm.py`), so each frame can be paired with where the camera was.

**API** turns protocol commands into typed capabilities (`harwood0_api.robot.Robot`). Each capability is defined once, and its docstring and Pydantic types describe it. The HTTP routes are thin adapters over these methods, and agent tool interfaces (such as an MCP server) wrap the same methods. The API also consumes the camera streams for depth estimation, object detection, and 3D reconstruction, and re-serves them to a browser viewer at `/`. The transport is swappable:

- `TcpTransport` talks to the firmware over WiFi, and pings it on a heartbeat while connected so motions that outlast a request keep running.
- `SimTransport` simulates the firmware in process, with the same validation, limits, and timing, for development and tests without hardware.

**Platform connection.** The API can join the dalnamics platform as a device (`harwood0_api.platform`). It registers once: given a one-time code from `cli devices register` or studio's Devices page, it does an MQTT handshake with devicemgr and stores the device ID and secret it gets back in `device.json` (owner-only) in its state directory. From then on it connects to the broker as that device and keeps the session open, reconnecting when it drops. While connected it publishes an empty heartbeat to `devices/{device id}/heartbeat` right after each connect and then every `HARWOOD0_PLATFORM_HEARTBEAT_S`, which keeps it shown as online. The platform counts only heartbeats, so other traffic doesn't replace them. Every device publish goes through one helper (`DeviceLink.publish`). Stored credentials always win over a code. Startup fails with a message saying what to do when the robot has neither, when the code is rejected or the handshake times out, or when the broker rejects the stored credentials. Without `HARWOOD0_MQTT_URL`, the API never touches the platform. The platform side is in the repo's [docs/devices.md](../../docs/devices.md).

| Variable | Default | Purpose |
|---|---|---|
| `HARWOOD0_PORT` | `47800` | HTTP port of the API and viewer; set a different one per API to run several |
| `HARWOOD0_MQTT_URL` | empty (no platform connection) | Platform broker, e.g. `mqtt://localhost:1883` for the local compose stack |
| `HARWOOD0_REGISTRATION_CODE` | empty | One-time code; used only while no credentials are stored |
| `HARWOOD0_DEVICE_NAME` | the hostname | Name shown in studio and `cli devices list` |
| `HARWOOD0_STATE_DIR` | `~/.local/state/harwood0` | Where `device.json` is kept |
| `HARWOOD0_PLATFORM_HEARTBEAT_S` | `30` | Seconds between platform heartbeats; must be a finite number greater than 0. Keep it at most a third of devicemgr's `DEVICEMGR_OFFLINE_AFTER`. Unrelated to `HARWOOD0_HEARTBEAT_S`, the firmware keep-alive ping |

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
| Camera stream | MJPEG over HTTP | The OV2640 encodes JPEG in hardware, so the ESP32 only forwards frames. Browsers show MJPEG in an `<img>` tag with no player, and each part carries `Content-Length` so the API splits frames without decoding. |
| API | Python + FastAPI | Python has the strongest robotics and vision ecosystem (OpenCV, PyTorch depth and detection models, Open3D) and a first-class MCP SDK for agent tooling. FastAPI generates an OpenAPI description of every capability. |
| Firmware ↔ API link | Newline-delimited JSON over TCP (WiFi) and serial | The same framing on every transport, human-readable, and debuggable with `nc`. No broker or extra infrastructure. |
| API ↔ platform link | MQTT 5 with aiomqtt | The platform's device transport. aiomqtt is asyncio-native, so the connection runs inside the API's event loop. |

## Testing

- `cad/tests`: geometry validity, build-volume checks, key features, assembly interference and tipping in every named arm pose, reach, cable clearance over a sweep of poses, and agreement with the firmware's limits.
- `firmware/test`: protocol and motion logic compiled and run on the host (`pio test -e native`). The protocol (`lib/protocol`) and the motion maths (`lib/motion`: limits, mecanum mixing, servo pulses, track steps) have no Arduino dependencies, so they can be tested without hardware.
- `api/tests`: HTTP routes against the simulator with an injected clock, the simulator's validation, the TCP transport and heartbeat against a local fake firmware server, the camera reader, its reconnects, and the camera routes against a mock MJPEG stream, and platform registration, credential storage, the device connection, and its heartbeats against a fake MQTT client.
- On hardware, `make check-robot` reaches the firmware through the API's transport and capability layer and times round trips. With the `hello` firmware (`firmware/src/hello`), which serves the protocol without driving any hardware, it checks WiFi and the link on a bare board ([hardware.md](hardware.md#connectivity-check)).
