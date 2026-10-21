# harwood0

A developer-focused, 3D-printable mecanum rover with a work table on top and a four-axis arm on a track beside it. It can pick things up from the table or the floor ahead of it. Its two cameras, one in the nose and one on the gripper, stream video to an API for depth estimation, object detection, and 3D scene reconstruction. Its capabilities are exposed so that an agentic AI controller can pilot it.

| Directory | What | Stack |
|---|---|---|
| [`cad/`](cad/) | Printed parts, hardware models, assembly, renders | Python, [build123d](https://build123d.readthedocs.io/), PyVista |
| [`firmware/`](firmware/) | Motion controller: drive, arm, track, safety | Arduino Uno R4 WiFi, [PlatformIO](https://platformio.org/) |
| [`camera/`](camera/) | Camera firmware: JPEG stream over WiFi | ESP32-CAM, [PlatformIO](https://platformio.org/) |
| [`api/`](api/) | Control API exposing robot capabilities, and a camera viewer | Python, FastAPI, TCP transport to firmware |
| [`docs/`](docs/) | Architecture, hardware (BOM, wiring, assembly), protocol | Markdown |

See [docs/architecture.md](docs/architecture.md) for how the pieces fit together and why each tool was chosen, and [docs/hardware.md](docs/hardware.md) to build one.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) for both Python projects
- [PlatformIO Core](https://docs.platformio.org/en/latest/core/installation/index.html) (`brew install platformio`)
- VS Code with the [OCP CAD Viewer](https://marketplace.visualstudio.com/items?itemName=bernhard-42.ocp-cad-viewer) and [PlatformIO IDE](https://marketplace.visualstudio.com/items?itemName=platformio.platformio-ide) extensions (recommended)

## Common tasks

```sh
make test          # all tests: CAD geometry, fit, and cable checks, firmware host tests, API tests
make cad           # export printed parts to cad/build/stl/ and cad/build/step/, by body, tower, and arm
make render        # render the assembly, parts, and hardware to cad/renders/*.png
make show          # open the robot and each module in OCP CAD Viewer (VS Code)
make cables        # cable cut list over the arm's and carriage's full range
make stability     # mass, centre of mass, and tipping margin
make firmware      # build firmware for the Uno R4 WiFi
make flash         # build, upload, and open the serial monitor
make flash-hello   # flash the connectivity-check firmware, which drives no hardware
make check-robot   # check the API can reach the robot (HARWOOD0_ROBOT_URL) and read its state
make camera        # build the camera firmware
make flash-camera  # flash a camera (CAMERA=nose or arm) and open the serial monitor
make api-sim       # run the API against the in-process simulator on :8000
make api           # run the API against real hardware (HARWOOD0_ROBOT_URL), viewer on :8000
```

Before the first firmware build, copy `firmware/include/secrets.example.h` to `firmware/include/secrets.h` and set your WiFi credentials. Do the same in `camera/include/` before the first camera build.

## Registering with the dalnamics platform

The API can connect to the platform as a device, so it shows up in studio and `cli devices list` for your account. With the platform stack running (`make up` in the repo root):

1. Get a one-time code from studio's Devices page (Register) or `cli devices register`. Codes expire after 10 minutes and work once.
2. Start the API with the broker URL and the code:

   ```sh
   HARWOOD0_MQTT_URL=mqtt://localhost:1883 HARWOOD0_REGISTRATION_CODE=AB3D7K make api-sim
   ```

   It registers, saves its credentials to `~/.local/state/harwood0/device.json` (`HARWOOD0_STATE_DIR` relocates it), and stays connected.
3. Later runs need only `HARWOOD0_MQTT_URL`; the stored credentials are reused, and a code, if set, is ignored.

The local platform stack also seeds the code `000000` for `dev@dalnamics.local`. It never expires and works once after each api start, so `HARWOOD0_REGISTRATION_CODE=000000` skips step 1.

To register again, for example after the platform's database is reset, delete `device.json` and repeat with a new code. `HARWOOD0_DEVICE_NAME` sets the name shown on the platform (default: the hostname). Without `HARWOOD0_MQTT_URL`, the API runs standalone.
