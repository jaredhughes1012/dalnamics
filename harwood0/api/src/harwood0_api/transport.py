"""Transports carry protocol requests to the robot (see docs/protocol.md).

Every transport speaks the same request/response protocol, so the capability
layer never knows whether it is talking to real firmware or the simulator.
"""

import asyncio
import itertools
import json
import logging
import math
import time
from collections.abc import Callable
from typing import Any, ClassVar, Protocol
from urllib.parse import urlparse

from harwood0_api.config import SIM, Settings

log = logging.getLogger(__name__)


class RobotError(Exception):
    """The robot rejected a request."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class RobotUnavailable(Exception):
    """The robot could not be reached or did not respond in time."""


class Transport(Protocol):
    async def request(self, cmd: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
        """Send a command and return its result, raising RobotError on failure."""
        ...

    async def close(self) -> None: ...


def _result(response: dict[str, Any]) -> dict[str, Any]:
    if not response.get("ok"):
        raise RobotError(response.get("error", "unknown"))
    return response.get("result", {})


class TcpTransport:
    """Talks to the firmware's TCP server, matching responses to requests by id.

    Messages are newline-delimited JSON, the same framing the firmware uses over serial.
    While connected it pings every `heartbeat_s` (0 disables this), so the firmware's
    command timeout does not stop motions that outlast a request.
    """

    def __init__(self, url: str, timeout_s: float, heartbeat_s: float = 0.3):
        parsed = urlparse(url)
        if parsed.scheme != "tcp" or not parsed.hostname or not parsed.port:
            raise ValueError(f"expected tcp://host:port, got {url!r}")
        self._url = url
        self._host = parsed.hostname
        self._port = parsed.port
        self._timeout_s = timeout_s
        self._heartbeat_s = heartbeat_s
        self._ids = itertools.count(1)
        self._pending: dict[int, asyncio.Future[dict[str, Any]]] = {}
        self._writer: asyncio.StreamWriter | None = None
        self._reader: asyncio.Task[None] | None = None
        self._heartbeat: asyncio.Task[None] | None = None
        self._connect_lock = asyncio.Lock()

    async def _ensure_connected(self) -> asyncio.StreamWriter:
        async with self._connect_lock:
            if self._writer is None:
                try:
                    reader, self._writer = await asyncio.wait_for(
                        asyncio.open_connection(self._host, self._port), self._timeout_s
                    )
                except (OSError, TimeoutError) as e:
                    raise RobotUnavailable(f"cannot connect to {self._url}: {e}") from e
                self._reader = asyncio.create_task(self._read(reader, self._writer))
                if self._heartbeat_s > 0:
                    self._heartbeat = asyncio.create_task(self._beat(self._writer))
            return self._writer

    async def _beat(self, writer: asyncio.StreamWriter) -> None:
        # Runs only for the connection it was started on, so it never reconnects by itself.
        while True:
            await asyncio.sleep(self._heartbeat_s)
            if self._writer is not writer:
                return
            try:
                await self.request("ping")
            except (RobotError, RobotUnavailable) as e:
                log.warning("heartbeat failed: %s", e)

    def _stop_heartbeat(self) -> asyncio.Task[None] | None:
        heartbeat, self._heartbeat = self._heartbeat, None
        if heartbeat is not None:
            heartbeat.cancel()
        return heartbeat

    async def _read(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            async for line in reader:
                try:
                    response = json.loads(line)
                except json.JSONDecodeError:
                    log.warning("dropping malformed line from robot: %r", line)
                    continue
                future = self._pending.pop(response.get("id"), None)
                if future and not future.done():
                    future.set_result(response)
            log.info("robot connection closed")
        except OSError as e:
            log.info("robot connection lost: %s", e)
        finally:
            self._writer = None
            self._stop_heartbeat()
            writer.close()
            for future in self._pending.values():
                if not future.done():
                    future.set_exception(RobotUnavailable("connection closed"))
            self._pending.clear()

    async def request(self, cmd: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
        writer = await self._ensure_connected()
        request_id = next(self._ids)
        future = asyncio.get_running_loop().create_future()
        self._pending[request_id] = future
        message = {"id": request_id, "cmd": cmd}
        if args:
            message["args"] = args
        try:
            writer.write(json.dumps(message).encode() + b"\n")
            await writer.drain()
            response = await asyncio.wait_for(future, self._timeout_s)
        except TimeoutError as e:
            raise RobotUnavailable(f"{cmd} timed out after {self._timeout_s}s") from e
        except OSError as e:
            raise RobotUnavailable(f"{cmd} failed: {e}") from e
        finally:
            self._pending.pop(request_id, None)
        return _result(response)

    async def close(self) -> None:
        heartbeat = self._stop_heartbeat()
        if heartbeat is not None:
            await asyncio.wait({heartbeat})
        if self._writer is not None:
            self._writer.close()
        if self._reader is not None:
            await self._reader


def _slew(current: float, target: float, max_step: float) -> float:
    return max(current - max_step, min(current + max_step, target))


def _number(args: dict[str, Any], key: str, default: float) -> float:
    """An optional numeric argument, as the firmware reads it: absent or null keeps `default`."""
    value = args.get(key)
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        raise RobotError("bad_args")
    return float(value)


def _only_keys(args: dict[str, Any], allowed: tuple[str, ...]) -> None:
    if any(key not in allowed for key in args):
        raise RobotError("bad_args")


class SimTransport:
    """In-process simulator of the firmware (protocol v1), for development without hardware.

    It validates and fails requests exactly as the firmware does. Motion is computed lazily
    from `clock` (seconds, default time.monotonic) at each request, so tests can inject a
    clock and step it. It has no command timeout: the TCP heartbeat keeps the real firmware's
    from firing, and the simulator stands in for both.
    """

    COMMANDS = ("ping", "info", "stop", "drive", "arm", "track", "home", "state")

    # Mirrors firmware/lib/motion/motion.h, firmware/include/config.h and protocol.h.
    JOINTS = ("yaw", "shoulder", "elbow", "grip")
    JOINT_LIMITS: ClassVar[dict[str, tuple[float, float]]] = {
        "yaw": (-90.0, 90.0),
        "shoulder": (-90.0, 90.0),
        "elbow": (-170.0, 0.0),
        "grip": (0.0, 90.0),
    }
    PARK_POSE: ClassVar[dict[str, float]] = {
        "yaw": 0.0,
        "shoulder": 45.0,
        "elbow": -130.0,
        "grip": 0.0,
    }
    SERVO_DEG_PER_S = 60.0
    TRACK_END = 67.0  # the slot's end walls
    TRACK_LIMITS = (-65.0, 65.0)
    TRACK_MM_PER_S = 12.0
    HOME_S = 2.0  # the real run takes up to about 20 s; the simulator is quicker
    MAX_DRIVE_MS = 5000
    DEFAULT_DRIVE_MS = 500

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._started = self._now = clock()
        self.stop_count = 0
        self._velocity = (0.0, 0.0, 0.0)
        self._drive_ms = 0
        self._drive_started = self._now
        self._arm_enabled = False
        self._joints = dict(self.PARK_POSE)
        self._targets = dict(self.PARK_POSE)
        self._homed = False
        self._homing = False
        self._home_left_s = 0.0
        self._x = 0.0
        self._track_target = 0.0

    async def request(self, cmd: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
        self._advance()
        if args is not None and not isinstance(args, dict):
            raise RobotError("bad_args")
        args = args or {}
        match cmd:
            case "ping":
                return {"uptime_ms": self._uptime_ms()}
            case "info":
                return self._info()
            case "stop":
                self._stop()
            case "drive":
                self._drive(args)
            case "arm":
                self._arm(args)
            case "track":
                self._track(args)
            case "home":
                self._homing, self._homed = True, False
                self._home_left_s = self.HOME_S
            case "state":
                return self._state()
            case _:
                raise RobotError("unknown_command")
        return {}

    async def close(self) -> None:
        pass

    def _uptime_ms(self) -> int:
        return round((self._now - self._started) * 1000)

    def _drive_ms_left(self) -> int:
        return max(0, self._drive_ms - round((self._now - self._drive_started) * 1000))

    def _advance(self) -> None:
        """Bring every motion up to the clock's current time."""
        now = self._clock()
        dt, self._now = max(0.0, now - self._now), now
        if self._drive_ms_left() == 0:
            self._velocity, self._drive_ms = (0.0, 0.0, 0.0), 0
        if self._arm_enabled:
            for joint in self.JOINTS:
                step = self.SERVO_DEG_PER_S * dt
                self._joints[joint] = _slew(self._joints[joint], self._targets[joint], step)
        if self._homing:
            if dt < self._home_left_s:
                self._home_left_s -= dt
                return
            # Against the rear wall: that is home. Back off to the travel's rear limit.
            dt -= self._home_left_s
            self._homing, self._homed = False, True
            self._x, self._track_target = -self.TRACK_END, self.TRACK_LIMITS[0]
        if self._homed:
            self._x = _slew(self._x, self._track_target, self.TRACK_MM_PER_S * dt)

    def _info(self) -> dict[str, Any]:
        limits: dict[str, Any] = {j: list(r) for j, r in self.JOINT_LIMITS.items()}
        limits["track"] = list(self.TRACK_LIMITS)
        limits["drive_ms"] = self.MAX_DRIVE_MS
        return {
            "name": "harwood0-sim",
            "firmware": "sim",
            "protocol": 1,
            "commands": list(self.COMMANDS),
            "limits": limits,
        }

    def _stop(self) -> None:
        self.stop_count += 1
        self._velocity, self._drive_ms = (0.0, 0.0, 0.0), 0
        self._targets = dict(self._joints)  # hold the arm where it is
        self._track_target = self._x
        if self._homing:
            self._homing = self._homed = False  # stopped part way, so the position is unknown

    def _drive(self, args: dict[str, Any]) -> None:
        keys = ("vx", "vy", "wz", "ms")
        _only_keys(args, keys)
        velocity = []
        for key in keys[:3]:
            v = _number(args, key, 0.0)
            if abs(v) > 1:
                raise RobotError("out_of_range")
            velocity.append(v)
        ms = _number(args, "ms", self.DEFAULT_DRIVE_MS)
        if not 0 <= ms <= self.MAX_DRIVE_MS:
            raise RobotError("out_of_range")
        self._drive_ms = int(ms)
        self._drive_started = self._now
        self._velocity = tuple(velocity) if self._drive_ms else (0.0, 0.0, 0.0)

    def _arm(self, args: dict[str, Any]) -> None:
        _only_keys(args, self.JOINTS)
        targets = {}
        for joint in self.JOINTS:
            if args.get(joint) is None:
                continue
            degrees = _number(args, joint, 0.0)
            lo, hi = self.JOINT_LIMITS[joint]
            if not lo <= degrees <= hi:
                raise RobotError("out_of_range")
            targets[joint] = degrees
        if not targets:
            raise RobotError("bad_args")
        if not self._arm_enabled:
            # Unknown starting position: assume parked.
            self._joints = dict(self.PARK_POSE)
            self._targets = dict(self.PARK_POSE)
            self._arm_enabled = True
        self._targets.update(targets)

    def _track(self, args: dict[str, Any]) -> None:
        _only_keys(args, ("x",))
        x = _number(args, "x", math.nan)
        if math.isnan(x):
            raise RobotError("bad_args")
        lo, hi = self.TRACK_LIMITS
        if not lo <= x <= hi:
            raise RobotError("out_of_range")
        if self._homing:
            raise RobotError("busy")
        if not self._homed:
            raise RobotError("not_homed")
        self._track_target = x

    def _state(self) -> dict[str, Any]:
        vx, vy, wz = self._velocity
        return {
            "drive": {"vx": vx, "vy": vy, "wz": wz, "ms_left": self._drive_ms_left()},
            "arm": {
                "enabled": self._arm_enabled,
                "joints": dict(self._joints),
                "targets": dict(self._targets),
            },
            "track": {
                "homed": self._homed,
                "homing": self._homing,
                "x": self._x if self._homed else None,
                "target": self._track_target if self._homed else None,
            },
        }


def make_transport(settings: Settings) -> Transport:
    if settings.robot_url == SIM:
        return SimTransport()
    return TcpTransport(settings.robot_url, settings.request_timeout_s, settings.heartbeat_s)
