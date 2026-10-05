"""Fit, reach, and stability checks for the robot in every named arm pose.

Parts touching face-to-face is fine (zero overlap volume); anything more means a
part, a placement, or a pose is wrong.
"""

import itertools

import pytest

from harwood0_cad.arm import GROUND_TARGET_X, GROUND_TARGET_Z, POSES, TABLE_TOP_Z, tip
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
