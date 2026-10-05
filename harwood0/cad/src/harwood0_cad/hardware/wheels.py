"""Mecanum wheel with its shaft coupling."""

import math

from build123d import Part, Pos, Rot

from harwood0_cad.shapes import cylinder

# 80 mm mecanum wheel with a 4 mm D-bore coupling for GA25-class motors.
WHEEL_D = 80.0
WHEEL_W = 36.0
WHEEL_ROLLERS = 9
WHEEL_ROLLER_D = 14.0
WHEEL_ROLLER_L = 30.0
WHEEL_HUB_D = 48.0
WHEEL_PLATE_D = 58.0
COUPLING_D = 14.0
COUPLING_L = 10.0  # from the wheel's inner face towards the motor


def mecanum_wheel(hand: int = 1) -> Part:
    """Origin at the wheel centre, axis along Z, coupling towards -Z.

    `hand` (+1 or -1) sets the roller angle: a set is two of each.
    """
    hw = WHEEL_W / 2
    wheel = cylinder(WHEEL_HUB_D / 2, (-hw + 2, hw - 2))
    for z in (-hw, hw - 2):
        wheel += cylinder(WHEEL_PLATE_D / 2, (z, z + 2))
    wheel += cylinder(COUPLING_D / 2, (-hw - COUPLING_L, -hw))
    wheel -= cylinder(2.0, (-hw - COUPLING_L - 1, -hw + 1))

    radius = WHEEL_D / 2 - WHEEL_ROLLER_D / 2
    roller = cylinder(WHEEL_ROLLER_D / 2, (-WHEEL_ROLLER_L / 2, WHEEL_ROLLER_L / 2))
    roller = Pos(radius, 0, 0) * Rot(hand * 45, 0, 0) * roller
    for i in range(WHEEL_ROLLERS):
        wheel += Rot(0, 0, i * 360 / WHEEL_ROLLERS) * roller
    return wheel


# Wheel's farthest extent below its axis, for ground-clearance maths.
WHEEL_RADIUS = WHEEL_D / 2
assert math.isclose(WHEEL_RADIUS, 40.0)
