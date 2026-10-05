"""Cable routing: every run's path, at the cable's real thickness, is clear of the printed
parts, wheels, motors, and the servo driver and its plugs in every named pose; and the
ribbon's rolling loop fits and stays in its channel over the full travel."""

import pytest

from harwood0_cad import params as p
from harwood0_cad.arm import CARRIAGE_RANGE, POSES, Pose
from harwood0_cad.arm_geometry import RIBBON_SLOT
from harwood0_cad.assembly import robot
from harwood0_cad.cables import RUNS, _ribbon, cable_shape

TOLERANCE = 0.5  # mm^3
OBSTACLES = ("wheel", "motor", "pca9685", "plug")


def _bbox_overlap(a, b) -> bool:
    ba, bb = a.bounding_box(), b.bounding_box()
    return all(
        lo_a < hi_b and lo_b < hi_a
        for lo_a, hi_a, lo_b, hi_b in zip(ba.min, ba.max, bb.min, bb.max)
    )


@pytest.mark.parametrize("pose_name", sorted(POSES))
def test_cables_clear(pose_name):
    pose = POSES[pose_name]
    obstacles = [i for i in robot(pose) if i.printed or i.name.startswith(OBSTACLES)]
    clashes = []
    for run in RUNS:
        cable = cable_shape(run, pose)
        for item in obstacles:
            if _bbox_overlap(cable, item.shape):
                volume = (cable & item.shape).volume
                if volume > TOLERANCE:
                    clashes.append(f"{run.name} x {item.name}: {volume:.1f} mm^3")
    assert not clashes, "\n".join(clashes)


@pytest.mark.parametrize("carriage_x", [CARRIAGE_RANGE[0], 0.0, CARRIAGE_RANGE[1]])
def test_ribbon_curl_stays_in_channel(carriage_x):
    xs = [pt.X for pt in _ribbon(Pose(carriage_x=carriage_x))]
    assert min(xs) >= p.CABLE_CHANNEL_X[0] and max(xs) <= p.CABLE_CHANNEL_X[1]


def test_ribbon_fits_its_channel_port_and_clamp():
    width = p.CABLE_CHANNEL_Y[1] - p.CABLE_CHANNEL_Y[0]
    assert width >= p.RIBBON_WIDTH + 0.5, "channel too narrow for the ribbon"
    assert p.CABLE_CHANNEL_DEPTH >= p.RIBBON_THICKNESS + 0.5, "channel too shallow for the ribbon"
    slot_x, slot_y = (hi - lo for lo, hi in RIBBON_SLOT)
    assert slot_y >= p.RIBBON_WIDTH + 0.5 and slot_x >= p.RIBBON_THICKNESS + 0.5, (
        "clamp slot too small"
    )


SWEEP_PARTS = ("tower", "hood", "carriage")


@pytest.mark.parametrize("yaw", list(range(-90, 91, 15)))
def test_moving_cables_clear_the_tower_at_any_yaw(yaw):
    """The named poses don't cover every yaw angle; sweep it against the parts the arm's
    leads pass close to as they turn."""
    pose = Pose(yaw=float(yaw), shoulder=30.0, elbow=-90.0)
    parts = [i for i in robot(pose) if i.name in SWEEP_PARTS]
    clashes = []
    for run in (
        r for r in RUNS if r.moving and not r.name.startswith("track") and "ribbon" not in r.name
    ):
        cable = cable_shape(run, pose)
        for item in parts:
            if _bbox_overlap(cable, item.shape) and (cable & item.shape).volume > TOLERANCE:
                clashes.append(f"{run.name} x {item.name}")
    assert not clashes, "\n".join(clashes)
