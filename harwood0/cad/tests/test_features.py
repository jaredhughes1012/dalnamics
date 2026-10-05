"""Checks that the openings and fixings the wiring and assembly depend on actually exist.

Each case names a point that must be solid (a clip, a tab, a standoff) or empty (a hole,
a slot, a channel) in a part's own frame, so a feature that silently fails to cut or
join shows up here.
"""

import pytest

from harwood0_cad import params as p
from harwood0_cad.parts import PARTS

CHASSIS_WALL_TOP = p.SUPPORT_Z - p.FLOOR_Z
CHANNEL_Y = sum(p.CABLE_CHANNEL_Y) / 2

FEATURES = [
    # (part, point, should be solid, what it is)
    ("tower", (0.0, -22.0, 98.0), False, "access door opening"),
    ("tower_door", (0.0, -24.0, 98.0), True, "access door"),
    ("tower", (11.4, 10.5, 98.0 + 27.95), True, "servo driver boss"),
    ("tower", (12.0, -17.1, 150.0), True, "hood joint corner block"),
    ("tower", (0.0, 0.0, 160.0), False, "column ends below the hood"),
    ("hood", (0.0, -4.5, 155.0), False, "hood floor pass into the column"),
    ("hood", (0.0, 74.8, 155.3), False, "arm cable hole in the hood floor"),
    ("hood", (0.0, 30.0, 185.0), False, "hood open on top, under the lid"),
    ("hood_lid", (0.0, 30.0, 185.0), True, "hood lid"),
    ("hood", (11.5, 4.0, 175.0), True, "hood lid snap arm"),
    ("carriage", (0.0, 0.0, 37.0), False, "deck cable hole"),
    ("carriage", (-11.0, 5.25, 30.0), False, "motor plate wire notch"),
    ("carriage", (-30.0, 30.0, 7.5), True, "ribbon clamp tab"),
    ("carriage", (-16.5, 30.75, 7.5), False, "ribbon slot in the clamp tab"),
    ("top_plate", (0.0, CHANNEL_Y, 5.0), False, "cable channel"),
    ("top_plate", (0.0, CHANNEL_Y, 1.5), True, "cable channel floor"),
    ("top_plate", (96.0, CHANNEL_Y, 1.5), False, "cable port"),
    ("chassis", (0.0, 57.0, CHASSIS_WALL_TOP - 12.0), False, "left motor wall wire hole"),
    ("chassis", (0.0, -57.0, CHASSIS_WALL_TOP - 12.0), False, "right motor wall wire hole"),
    ("chassis", (p.CHASSIS_L / 2 - 3.0 - 1.5, 40.0, CHASSIS_WALL_TOP + 3.0), True, "nose snap arm"),
    ("upper_arm", (7.5, 35.0, -12.0), False, "upper arm wire clip opening"),
    ("upper_arm", (10.5, 35.0, -13.8), True, "upper arm wire clip"),
    ("upper_arm", (10.5, 35.0, -12.0), False, "upper arm wire clip's side gap"),
    ("forearm", (7.0, 18.0, 12.0), False, "forearm wire clip opening"),
    ("forearm", (10.5, 18.0, 13.8), True, "forearm wire clip"),
    ("forearm", (10.5, 18.0, 12.0), False, "forearm wire clip's side gap"),
    ("gripper_base", (20.0, 52.0, 14.7), True, "arm camera cradle rail"),
]


@pytest.fixture(scope="module")
def parts():
    return {name: PARTS[name]() for name in {f[0] for f in FEATURES}}


@pytest.mark.parametrize("part,point,solid,what", FEATURES, ids=[f[3] for f in FEATURES])
def test_feature(parts, part, point, solid, what):
    assert parts[part].is_inside(point) == solid, (
        f"{what}: expected {'solid' if solid else 'empty'} at {point}"
    )
