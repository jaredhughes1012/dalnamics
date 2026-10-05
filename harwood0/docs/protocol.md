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

The firmware records the time of every command it receives. If actuators are running and no command arrives within the command timeout (`kCommandTimeoutMs` in `firmware/include/config.h`), it stops all actuators. A controller that wants to keep moving must send commands, or `ping`, more often than the timeout.

## Commands

| Command | Args | Result | Effect |
|---|---|---|---|
| `ping` | none | `{"uptime_ms": int}` | None. Resets the command timeout. |
| `info` | none | `{"name": str, "firmware": str, "protocol": int, "commands": [str]}` | None. |
| `stop` | none | none | Stops all actuators immediately. |

## Errors

| Code | Meaning |
|---|---|
| `bad_json` | The request could not be parsed. |
| `unknown_command` | `cmd` is not a supported command. |
