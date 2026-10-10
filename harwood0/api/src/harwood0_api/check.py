"""Connectivity check: reach the robot through the same transport and capability layer as the
API, read its info and state, and time a few round trips. Exits non-zero on any failure.

    HARWOOD0_ROBOT_URL=tcp://<robot-ip>:7777 uv run harwood0-check
"""

import argparse
import asyncio
import statistics
import sys
import time
from collections.abc import Callable
from dataclasses import replace

from harwood0_api.config import Settings
from harwood0_api.robot import Robot, RobotState
from harwood0_api.transport import RobotError, RobotUnavailable, make_transport


def _summarise(state: RobotState) -> str:
    drive = f"driving ({state.drive.ms_left} ms left)" if state.drive.ms_left else "stopped"
    arm = "enabled" if state.arm.enabled else "limp"
    if state.track.homing:
        track = "homing"
    elif state.track.homed:
        track = f"at {state.track.x:.1f} mm"
    else:
        track = "unhomed"
    return f"drive {drive}, arm {arm}, track {track}"


async def check(robot: Robot, pings: int, out: Callable[[str], None] = print) -> bool:
    """Run each step in turn, reporting as it goes. Returns whether every step passed."""
    steps = 0

    def report(name: str, detail: str) -> None:
        nonlocal steps
        steps += 1
        out(f"  {name:<10} ok    {detail}")

    try:
        start = time.perf_counter()
        ping = await robot.ping()
        report("connect", f"{_ms(start)} ms, firmware up {ping.uptime_ms / 1000:.1f} s")

        info = await robot.info()
        report("info", f"{info.name} firmware {info.firmware}, protocol {info.protocol}")

        state = await robot.state()
        report("state", _summarise(state))

        rtts = []
        for _ in range(pings):
            start = time.perf_counter()
            await robot.ping()
            rtts.append(_ms(start))
        if rtts:
            report(
                f"ping x{pings}",
                f"min {min(rtts)} / median {statistics.median(rtts):.0f} / max {max(rtts)} ms",
            )
    except (RobotUnavailable, RobotError, ValueError) as e:
        out(f"  {'FAILED':<10} after {steps} step(s): {type(e).__name__}: {e}")
        return False
    return True


def _ms(start: float) -> int:
    return round((time.perf_counter() - start) * 1000)


async def _run(settings: Settings, pings: int) -> bool:
    print(f"harwood0 check: {settings.robot_url}")
    # No heartbeat: the check moves nothing, and its own pings are the traffic being measured.
    try:
        transport = make_transport(replace(settings, heartbeat_s=0))
    except ValueError as e:
        print(f"  {e}")
        return False
    try:
        return await check(Robot(transport), pings)
    finally:
        await transport.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", help="robot URL (default: HARWOOD0_ROBOT_URL)")
    parser.add_argument("--pings", type=int, default=20, help="round trips to time")
    args = parser.parse_args()
    settings = Settings.from_env()
    if args.url:
        settings = replace(settings, robot_url=args.url)
    sys.exit(0 if asyncio.run(_run(settings, args.pings)) else 1)


if __name__ == "__main__":
    main()
