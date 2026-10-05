# Firmware protocol

The API and firmware exchange JSON messages. Every transport carries the same messages:

- **TCP** on port 7777 over WiFi. The firmware accepts one client at a time; a new connection replaces the old one.
- **Serial** at 115200 baud over USB.

On both, each message is one line of JSON terminated by `\n`. You can talk to the robot by hand with `nc <robot-ip> 7777`. The Uno does not advertise itself over mDNS, so find its IP address in the serial log at boot (or reserve one on your router) and set `HARWOOD0_ROBOT_URL=tcp://<ip>:7777` for the API.

The protocol version is reported by `info` and is bumped on any breaking change.

## Requests and responses

```json
{"id": 7, "cmd": "ping", "args": {}}
```

- `id`: an integer chosen by the client and echoed in the response, so a client can have several requests in flight.
- `cmd`: the command name.
- `args`: optional, command-specific.

A successful response:

```json
{"id": 7, "ok": true, "result": {"uptime_ms": 1234}}
```

A failed response:

```json
{"id": 7, "ok": false, "error": "unknown_command"}
```

If the request is not valid JSON, `id` is `null` and `error` is `bad_json`.

## Safety

The firmware records the time of every command it receives. If anything is moving (wheels, arm, or carriage) and no command arrives within the command timeout (`kCommandTimeoutMs` in `firmware/include/config.h`, 1 s), it stops all actuators. A controller that wants to keep moving must send commands, or `ping`, more often than the timeout. The API does this for you with a heartbeat while it is connected.

Drive commands also expire on their own after `ms` milliseconds (at most 5 s), so the wheels never keep turning on a stale command even while the heartbeat runs.

`stop` (and the timeout) stops the wheels and the carriage, and holds each servo where it is: cutting the servos would drop the arm.

## Units and frames

The conventions match the CAD (`cad/src/harwood0_cad/arm.py`):

- **Drive** velocities are fractions of full speed, from -1 to 1: `vx` forward, `vy` to the left, `wz` turning anticlockwise seen from above.
- **Arm** angles are in degrees:
  - `yaw`: 0 points the arm across the table, -90 straight ahead, +90 to the rear.
  - `shoulder`: the upper arm's elevation above horizontal.
  - `elbow`: the forearm's bend relative to the upper arm, negative bending down.
  - `grip`: the gripper gear's turn, 0 closed; 90 opens the fingers about 36 mm apart.
- **Track** position `x` is the carriage centre in mm along the body, positive towards the nose, 0 at the middle of the track.

The ranges are reported by `info` under `limits`. The firmware enforces only joint and track ranges: some combinations within them (for example the shoulder pointing down with the elbow straight) drive the arm into the table or body, so the controller must avoid them.

## Commands

| Command | Args | Result | Effect |
|---|---|---|---|
| `ping` | none | `{"uptime_ms": int}` | None. Resets the command timeout. |
| `info` | none | `{"name", "firmware", "protocol", "commands": [str], "limits": {...}}` | None. `limits` has `[min, max]` for each joint and `track`, and `drive_ms`, the longest drive. |
| `stop` | none | none | Stops the wheels and carriage, and holds the arm where it is. |
| `drive` | `vx`, `vy`, `wz` (default 0), `ms` (default 500, max 5000) | none | Drives the wheels at that velocity for `ms`, then stops them. Each drive replaces the last; `ms` 0 stops the wheels. |
| `arm` | any of `yaw`, `shoulder`, `elbow`, `grip` | none | Sets those joints' targets; the rest keep theirs. Every joint moves towards its target at 60°/s. |
| `track` | `x` | none | Moves the carriage to `x`. Needs homing first. |
| `home` | none | none | Runs the carriage back into the slot's rear end wall to find its position, then stops at the rear limit. Takes up to about 20 s. |
| `state` | none | see below | None. |

Commands that start a motion return as soon as it starts; poll `state` to see it finish.

### Arm at power-up

The servos are limp until the first `arm` command. Nothing reports their real position, so the firmware assumes the arm is in the park pose (yaw 0, shoulder 45, elbow -130, grip 0) and drives every servo there at once, then on to the commanded targets. Park the arm before switching off, so the first move does not jump.

### State

```json
{
  "drive": {"vx": 0.0, "vy": 0.0, "wz": 0.0, "ms_left": 0},
  "arm": {
    "enabled": true,
    "joints": {"yaw": 0.0, "shoulder": 45.0, "elbow": -130.0, "grip": 0.0},
    "targets": {"yaw": 0.0, "shoulder": 30.0, "elbow": -110.0, "grip": 0.0}
  },
  "track": {"homed": true, "homing": false, "x": -65.0, "target": -65.0}
}
```

`arm.joints` are the angles commanded to the servos so far, moving towards `targets`, not measured positions. `track.x` and `track.target` are `null` until the track is homed.

## Errors

| Code | Meaning |
|---|---|
| `bad_json` | The request could not be parsed. |
| `unknown_command` | `cmd` is not a supported command. |
| `bad_args` | An argument is missing, not a number, or not one the command takes. |
| `out_of_range` | An argument is outside its limit. Nothing moves. |
| `not_homed` | `track` was sent before the track was homed. |
| `busy` | `track` was sent while homing. |
