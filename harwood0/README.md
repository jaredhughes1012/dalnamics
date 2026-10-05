# harwood0

A developer-focused, 3D-printable mecanum rover with a work table on top and a four-axis arm on a track beside it. It can pick things up from the table or the floor ahead of it. Its two cameras, one in the nose and one on the gripper, stream video to an API for depth estimation, object detection, and 3D scene reconstruction. Its capabilities are exposed so that an agentic AI controller can pilot it.

| Directory | What | Stack |
|---|---|---|
| [`cad/`](cad/) | Printed parts, hardware models, assembly, renders | Python, [build123d](https://build123d.readthedocs.io/), PyVista |
| [`firmware/`](firmware/) | Motion controller: drive, arm, track, safety | Arduino Uno R4 WiFi, [PlatformIO](https://platformio.org/) |
| [`api/`](api/) | Control API exposing robot capabilities | Python, FastAPI, TCP transport to firmware |
| [`docs/`](docs/) | Architecture, hardware (BOM, wiring, assembly), protocol | Markdown |

See [docs/architecture.md](docs/architecture.md) for how the pieces fit together and why each tool was chosen, and [docs/hardware.md](docs/hardware.md) to build one.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) for both Python projects
- [PlatformIO Core](https://docs.platformio.org/en/latest/core/installation/index.html) (`brew install platformio`)
- VS Code with the [OCP CAD Viewer](https://marketplace.visualstudio.com/items?itemName=bernhard-42.ocp-cad-viewer) and [PlatformIO IDE](https://marketplace.visualstudio.com/items?itemName=platformio.platformio-ide) extensions (recommended)

## Common tasks

```sh
make test          # all tests: CAD geometry, fit, and cable checks, firmware host tests, API tests
make cad           # export printed parts to cad/build/*.stl and *.step
make render        # render the assembly, parts, and hardware to cad/renders/*.png
make show          # open the robot and each module in OCP CAD Viewer (VS Code)
make cables        # cable cut list over the arm's and carriage's full range
make stability     # mass, centre of mass, and tipping margin
make firmware      # build firmware for the Uno R4 WiFi
make flash         # build, upload, and open the serial monitor
make api-sim       # run the API against the in-process simulator on :8000
make api           # run the API against real hardware (HARWOOD0_ROBOT_URL)
```

Before the first firmware build, copy `firmware/include/secrets.example.h` to `firmware/include/secrets.h` and set your WiFi credentials.
