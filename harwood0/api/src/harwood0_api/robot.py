"""The robot's capabilities as typed operations.

This is the single definition of what harwood0 can do. The HTTP API (and
later, agent tool interfaces) are thin adapters over these methods, so each
capability's docstring doubles as its description for API and agent clients.
"""

from pydantic import BaseModel

from harwood0_api.transport import Transport


class Ping(BaseModel):
    uptime_ms: int


class RobotInfo(BaseModel):
    name: str
    firmware: str
    protocol: int
    commands: list[str]


class Robot:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def ping(self) -> Ping:
        """Check the robot is reachable and report how long its firmware has been running."""
        return Ping.model_validate(await self._transport.request("ping"))

    async def info(self) -> RobotInfo:
        """Describe the robot: name, firmware version, protocol version and supported commands."""
        return RobotInfo.model_validate(await self._transport.request("info"))

    async def stop(self) -> None:
        """Immediately stop all actuators."""
        await self._transport.request("stop")
