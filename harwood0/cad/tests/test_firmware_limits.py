"""The firmware's joint and track limits must match the CAD's, which the fit checks cover."""

import re
from pathlib import Path

import pytest

from harwood0_cad.arm import (
    CARRIAGE_RANGE,
    ELBOW_RANGE,
    GRIP_RANGE,
    POSES,
    SHOULDER_RANGE,
    YAW_RANGE,
)
from harwood0_cad.arm_geometry import PINION_MODULE, PINION_TEETH

MOTION_H = Path(__file__).resolve().parents[2] / "firmware" / "lib" / "motion" / "motion.h"


def _constant(name: str) -> list[float]:
    """Values of a float constant or `{...}` array in motion.h."""
    match = re.search(rf"\b{name}\b[^=]*=\s*(\{{[^}}]*\}}|[^;]+);", MOTION_H.read_text())
    assert match, f"{name} not found in {MOTION_H}"
    return [float(v.rstrip("f")) for v in re.findall(r"-?\d+(?:\.\d+)?f?", match.group(1))]


def test_joint_ranges_match():
    ranges = (YAW_RANGE, SHOULDER_RANGE, ELBOW_RANGE, GRIP_RANGE)
    assert _constant("kJointMin") == [lo for lo, _ in ranges]
    assert _constant("kJointMax") == [hi for _, hi in ranges]


def test_park_pose_matches():
    park = POSES["park"]
    assert _constant("kParkPose") == pytest.approx([park.yaw, park.shoulder, park.elbow, park.grip])


def test_track_matches():
    assert _constant("kTrackEnd") == [CARRIAGE_RANGE[1]]
    assert -CARRIAGE_RANGE[0] == CARRIAGE_RANGE[1]
    module, teeth = _constant("kPinionPitchCircumference")[1:]
    assert (module, teeth) == (PINION_MODULE, PINION_TEETH)
