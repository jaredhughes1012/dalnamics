"""The robot's capabilities as typed operations.

This is the single definition of what harwood0 can do. The HTTP API (and
later, agent tool interfaces) are thin adapters over these methods, so each
capability's docstring doubles as its description for API and agent clients.

Conventions (docs/protocol.md): drive velocities are fractions of full speed; arm angles
are degrees; the track position is mm along the body, positive towards the nose. The
joint and track ranges come from `info().limits`.
"""

from pydantic import BaseModel, Field

from harwood0_api.transport import Transport


class Ping(BaseModel):
    uptime_ms: int


class Limits(BaseModel):
    """Allowed ranges as [min, max]: joints in degrees, track in mm."""

    yaw: tuple[float, float]
    shoulder: tuple[float, float]
    elbow: tuple[float, float]
    grip: tuple[float, float]
    track: tuple[float, float]
    drive_ms: int = Field(description="Longest a single drive may run, in ms.")


class RobotInfo(BaseModel):
    name: str
    firmware: str
    protocol: int
    commands: list[str]
    limits: Limits


class Drive(BaseModel):
    """A body velocity, each component a fraction of full speed, held for `ms`."""

    vx: float = Field(0.0, ge=-1, le=1, description="Forward speed, -1 to 1.")
    vy: float = Field(0.0, ge=-1, le=1, description="Leftward speed, -1 to 1.")
    wz: float = Field(0.0, ge=-1, le=1, description="Anticlockwise turn seen from above, -1 to 1.")
    ms: int = Field(500, ge=0, le=5000, description="How long to drive before stopping, in ms.")


class ArmTargets(BaseModel):
    """Joint targets in degrees; joints left out keep their current target."""

    yaw: float | None = Field(None, description="0 across the table, -90 ahead, +90 rear.")
    shoulder: float | None = Field(None, description="Upper arm elevation above horizontal.")
    elbow: float | None = Field(None, description="Forearm bend from the upper arm, negative down.")
    grip: float | None = Field(None, description="0 closed; 40 opens the fingers ~17 mm.")


class TrackTarget(BaseModel):
    x: float = Field(description="Carriage centre in mm, positive towards the nose, 0 mid-track.")


class Joints(BaseModel):
    """Arm angles in degrees."""

    yaw: float
    shoulder: float
    elbow: float
    grip: float


class DriveState(BaseModel):
    vx: float
    vy: float
    wz: float
    ms_left: int = Field(description="Time until the current drive stops, in ms; 0 if stopped.")


class ArmState(BaseModel):
    enabled: bool = Field(description="False until the first arm command; servos are limp.")
    joints: Joints = Field(description="Angles commanded so far (not measured), moving to targets.")
    targets: Joints


class TrackState(BaseModel):
    homed: bool
    homing: bool
    x: float | None = Field(description="Carriage position in mm; null until homed.")
    target: float | None = Field(
        description="Where the carriage is heading in mm; null until homed."
    )


class RobotState(BaseModel):
    drive: DriveState
    arm: ArmState
    track: TrackState


class Robot:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def ping(self) -> Ping:
        """Check the robot is reachable and report how long its firmware has been running."""
        return Ping.model_validate(await self._transport.request("ping"))

    async def info(self) -> RobotInfo:
        """Describe the robot: name, firmware and protocol versions, supported commands, and
        `limits`: the [min, max] range of each arm joint (degrees) and the track (mm), and
        `drive_ms`, the longest single drive."""
        return RobotInfo.model_validate(await self._transport.request("info"))

    async def stop(self) -> None:
        """Immediately stop the wheels and the track carriage, and hold the arm where it is.
        Stopping during homing leaves the track unhomed."""
        await self._transport.request("stop")

    async def drive(self, vx: float = 0.0, vy: float = 0.0, wz: float = 0.0, ms: int = 500) -> None:
        """Drive the wheels for `ms` milliseconds (0-5000, default 500), then stop.

        Velocities are fractions of full speed from -1 to 1: `vx` forward, `vy` to the left,
        `wz` turning anticlockwise seen from above. Each drive replaces the previous one, so
        send another before `ms` runs out to keep moving."""
        args = Drive(vx=vx, vy=vy, wz=wz, ms=ms)
        await self._transport.request("drive", args.model_dump())

    async def move_arm(
        self,
        yaw: float | None = None,
        shoulder: float | None = None,
        elbow: float | None = None,
        grip: float | None = None,
    ) -> None:
        """Set targets for the given arm joints, in degrees; the rest keep theirs. Give at
        least one. Every joint moves towards its target at 60 degrees/s; this returns as soon
        as the move starts, so poll `state` to see it finish.

        `yaw`: 0 points the arm across the table, -90 straight ahead, +90 to the rear.
        `shoulder`: upper arm elevation above horizontal. `elbow`: forearm bend relative to
        the upper arm, negative bending down. `grip`: 0 closed, 40 opens the fingers about
        17 mm. Ranges are in `info().limits`. The first arm command after power-up starts
        from the park pose (yaw 0, shoulder 45, elbow -130, grip 0). Not every in-range
        combination is safe: avoid poses that drive the arm into the table or body."""
        args = ArmTargets(yaw=yaw, shoulder=shoulder, elbow=elbow, grip=grip)
        await self._transport.request("arm", args.model_dump(exclude_none=True))

    async def move_track(self, x: float) -> None:
        """Move the track carriage to `x` mm along the body (positive towards the nose, 0 at
        the middle; range in `info().limits.track`) at about 12 mm/s. The track must be homed
        first (`home_track`); fails with `not_homed` before that and `busy` while homing.
        Returns as soon as the move starts; poll `state` to see it finish."""
        await self._transport.request("track", TrackTarget(x=x).model_dump())

    async def home_track(self) -> None:
        """Home the track carriage: run it into the rear end wall to find its position, then
        stop at the rear limit. Takes up to about 20 s; returns at once, so poll `state`
        until `track.homed` is true. Needed before `move_track`."""
        await self._transport.request("home")

    async def state(self) -> RobotState:
        """Report what the robot is doing: the current drive and its time left, the arm's
        enabled flag, commanded joint angles and targets (degrees), and the track's homing
        status, position and target (mm; null until homed)."""
        return RobotState.model_validate(await self._transport.request("state"))
