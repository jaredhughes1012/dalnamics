"""Fit, reach, and stability checks for the robot in every named arm pose, plus fit checks at
the edges of the joint ranges.

Parts touching face-to-face is fine (zero overlap volume); anything more means a
part, a placement, or a pose is wrong.
"""

import itertools

import pytest

from harwood0_cad.arm import (
    ELBOW_RANGE,
    GROUND_TARGET_X,
    GROUND_TARGET_Z,
    POSES,
    SHOULDER_RANGE,
    TABLE_TOP_Z,
    Pose,
    tip,
)
from harwood0_cad.assembly import robot
from harwood0_cad.hardware import HARDWARE
from harwood0_cad.stability import MIN_TIP_MARGIN, tipping_margin

# Overlap volume (mm^3) below which a contact counts as face-to-face.
TOLERANCE = 0.5

# Pairs that are meant to engage: the pinion's teeth mesh with the rack in the top plate.
MESHING = {frozenset({"pinion", "top_plate"})}


def _bbox_overlap(a, b) -> bool:
    ba, bb = a.bounding_box(), b.bounding_box()
    return all(
        lo_a < hi_b and lo_b < hi_a
        for lo_a, hi_a, lo_b, hi_b in zip(ba.min, ba.max, bb.min, bb.max)
    )


@pytest.fixture(scope="module", params=sorted(POSES))
def posed(request):
    return request.param, robot(POSES[request.param])


def test_no_interference_with_printed_parts(posed):
    _, items = posed
    clashes = []
    for a, b in itertools.combinations(items, 2):
        if not (a.printed or b.printed) or frozenset({a.name, b.name}) in MESHING:
            continue
        if not _bbox_overlap(a.shape, b.shape):
            continue
        volume = (a.shape & b.shape).volume
        if volume > TOLERANCE:
            clashes.append(f"{a.name} x {b.name}: {volume:.1f} mm^3")
    assert not clashes, "\n".join(clashes)


def _clashes(pairs):
    """Overlaps between the given pairs of items, where at least one is printed."""
    found = []
    for a, b in pairs:
        if not (a.printed or b.printed) or not _bbox_overlap(a.shape, b.shape):
            continue
        volume = (a.shape & b.shape).volume
        if volume > TOLERANCE:
            found.append(f"{a.name} x {b.name}: {volume:.1f} mm^3")
    return found


# Everything that moves with the yaw bracket.
ARM = {
    "yaw_bracket",
    "shoulder_servo",
    "shoulder_horn",
    "upper_arm",
    "elbow_servo",
    "elbow_horn",
    "forearm",
    "arm_camera",
    "gripper_servo",
    "gripper_horn",
    "gripper_base",
    "gripper_gear",
    "gripper_jaw_front",
    "gripper_jaw_rear",
}


@pytest.mark.parametrize("shoulder", [SHOULDER_RANGE[0], 0.0, SHOULDER_RANGE[1]])
def test_elbow_folds_fully_without_hitting_the_arm(shoulder):
    arm = [i for i in robot(Pose(0.0, 0.0, shoulder, ELBOW_RANGE[0])) if i.name in ARM]
    clashes = _clashes(itertools.combinations(arm, 2))
    assert not clashes, "\n".join(clashes)


@pytest.mark.parametrize("yaw", range(-90, 91, 10))
def test_upper_arm_clears_the_tower_as_it_yaws(yaw):
    items = {i.name: i for i in robot(Pose(0.0, yaw, 0.0, -70.0))}
    pairs = [(items["upper_arm"], items[name]) for name in ("tower", "hood", "yaw_servo")]
    clashes = _clashes(pairs)
    assert not clashes, "\n".join(clashes)


def test_robot_does_not_tip(posed):
    name, items = posed
    margin = tipping_margin(items)
    assert margin >= MIN_TIP_MARGIN, (
        f"{name}: centre of mass only {margin:.0f} mm inside the wheels"
    )


@pytest.mark.parametrize("name", sorted(POSES))
def test_pose_within_joint_limits(name):
    assert POSES[name].within_limits()


@pytest.mark.parametrize("name", ["table_near", "table_far", "table_diagonal", "table_rear"])
def test_reaches_table(name):
    assert tip(POSES[name]).Z == pytest.approx(TABLE_TOP_Z + 8.0, abs=0.5)


def test_reaches_ground_ahead_of_nose():
    t = tip(POSES["ground_front"])
    assert t.X == pytest.approx(GROUND_TARGET_X, abs=0.5)
    assert t.Z == pytest.approx(GROUND_TARGET_Z, abs=0.5)


@pytest.mark.parametrize("name", sorted(HARDWARE))
def test_hardware_builds(name):
    shape = HARDWARE[name]()
    assert shape.volume > 0
