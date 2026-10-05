"""Transports carry protocol requests to the robot (see docs/protocol.md).

Every transport speaks the same request/response protocol, so the capability
layer never knows whether it is talking to real firmware or the simulator.
"""

import asyncio
import itertools
import json
import logging
import time
from typing import Any, Protocol
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
    """

    def __init__(self, url: str, timeout_s: float):
        parsed = urlparse(url)
        if parsed.scheme != "tcp" or not parsed.hostname or not parsed.port:
            raise ValueError(f"expected tcp://host:port, got {url!r}")
        self._url = url
        self._host = parsed.hostname
        self._port = parsed.port
        self._timeout_s = timeout_s
        self._ids = itertools.count(1)
        self._pending: dict[int, asyncio.Future[dict[str, Any]]] = {}
        self._writer: asyncio.StreamWriter | None = None
        self._reader: asyncio.Task[None] | None = None
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
            return self._writer

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
        if self._writer is not None:
            self._writer.close()
        if self._reader is not None:
            await self._reader


class SimTransport:
    """In-process stand-in for the firmware, for development without hardware."""

    COMMANDS = ("ping", "info", "stop")

    def __init__(self) -> None:
        self._started = time.monotonic()
        self.stop_count = 0

    async def request(self, cmd: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
        match cmd:
            case "ping":
                response = {"ok": True, "result": {"uptime_ms": self._uptime_ms()}}
            case "info":
                response = {
                    "ok": True,
                    "result": {
                        "name": "harwood0-sim",
                        "firmware": "sim",
                        "protocol": 0,
                        "commands": list(self.COMMANDS),
                    },
                }
            case "stop":
                self.stop_count += 1
                response = {"ok": True}
            case _:
                response = {"ok": False, "error": "unknown_command"}
        return _result(response)

    async def close(self) -> None:
        pass

    def _uptime_ms(self) -> int:
        return int((time.monotonic() - self._started) * 1000)


def make_transport(settings: Settings) -> Transport:
    if settings.robot_url == SIM:
        return SimTransport()
    return TcpTransport(settings.robot_url, settings.request_timeout_s)
