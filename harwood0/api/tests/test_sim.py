"""Checks SimTransport validates requests exactly as the firmware's protocol.cpp does."""

import asyncio
import math

import pytest

from harwood0_api.transport import RobotError, SimTransport


def call(cmd, args=None, sim=None):
    return asyncio.run((sim or SimTransport()).request(cmd, args))


def error(cmd, args=None, sim=None):
    with pytest.raises(RobotError) as exc:
        call(cmd, args, sim)
    return exc.value.code


def test_unknown_command():
    assert error("fly") == "unknown_command"


@pytest.mark.parametrize("args", [[], "x", 3])
def test_non_object_args(args):
    assert error("ping", args) == "bad_args"
    assert error("fly", args) == "bad_args"


@pytest.mark.parametrize(
    ("args", "code"),
    [
        ({"speed": 1}, "bad_args"),
        ({"vx": "1"}, "bad_args"),
        ({"vx": True}, "bad_args"),
        ({"vx": math.nan}, "bad_args"),
        ({"vx": -1.01}, "out_of_range"),
        ({"wz": 2}, "out_of_range"),
        ({"ms": 5001}, "out_of_range"),
        ({"ms": -1}, "out_of_range"),
        ({"vx": 2, "vy": "x"}, "out_of_range"),  # checked in order, as the firmware does
    ],
)
def test_drive_errors(args, code):
    assert error("drive", args) == code


def test_drive_accepts_limits():
    assert call("drive", {"vx": -1, "vy": 1, "wz": 0.0, "ms": 5000}) == {}


@pytest.mark.parametrize(
    ("args", "code"),
    [
        (None, "bad_args"),
        ({}, "bad_args"),
        ({"yaw": None}, "bad_args"),
        ({"wrist": 0}, "bad_args"),
        ({"yaw": "left"}, "bad_args"),
        ({"yaw": 91}, "out_of_range"),
        ({"elbow": 1}, "out_of_range"),
        ({"grip": -1}, "out_of_range"),
    ],
)
def test_arm_errors(args, code):
    assert error("arm", args) == code


@pytest.mark.parametrize(
    ("args", "code"),
    [
        (None, "bad_args"),
        ({}, "bad_args"),
        ({"x": None}, "bad_args"),
        ({"x": "0"}, "bad_args"),
        ({"x": 0, "y": 0}, "bad_args"),
        ({"x": -65.5}, "out_of_range"),
    ],
)
def test_track_errors(args, code):
    assert error("track", args) == code


def test_track_range_checked_before_homing():
    sim = SimTransport()
    call("home", sim=sim)
    assert error("track", {"x": 100}, sim) == "out_of_range"
    assert error("track", {"x": 0}, sim) == "busy"


def test_ping_ignores_args():
    assert "uptime_ms" in call("ping", {"anything": 1})
