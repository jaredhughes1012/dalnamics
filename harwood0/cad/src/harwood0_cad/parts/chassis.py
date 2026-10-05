"""Chassis tray: floor plus walls, carrying the four drive motors and the battery.

Each motor slides in from above and bolts through a side wall by its gearbox
face (2x M3), with its shaft poking out to the wheel. A saddle under each motor
holds it in place while you fit the screws. The battery and UBEC drop into corner
guides on the floor and are held down by the deck.

Local frame: the global XY origin, with Z=0 at the floor underside.
Printed as modelled, floor down, with no supports.
"""

from build123d import Axis, Part, fillet

from harwood0_cad import params as p
from harwood0_cad.hardware.battery import LIPO_H, LIPO_L, LIPO_W
from harwood0_cad.hardware.boards import UBEC_H, UBEC_L, UBEC_W
from harwood0_cad.hardware.motors import (
    GA25_BOSS_D,
    GA25_CAN_D,
    GA25_FACE_HOLE_SPACING,
    GA25_GEARBOX_L,
)
from harwood0_cad.shapes import box, corner_guides, cylinder

AXLE_H = p.AXLE_Z - p.FLOOR_Z
SADDLE_Y = p.MOTOR_FACE_Y - GA25_GEARBOX_L - 12  # under the motor can
BATTERY_GUIDE_H = 8.0
UBEC_GUIDE_H = 5.0
DECK_PILOT_DEPTH = 12.0


def chassis() -> Part:
    L, W, H = p.CHASSIS_L, p.CHASSIS_W, p.CHASSIS_H
    shell = box((-L / 2, L / 2), (-W / 2, W / 2), (0, H))
    shell = fillet(shell.edges().filter_by(Axis.Z), radius=p.CHASSIS_CORNER_R)
    inner_l, inner_w = L - 2 * p.END_WALL_T, W - 2 * p.SIDE_WALL_T
    cavity = box((-inner_l / 2, inner_l / 2), (-inner_w / 2, inner_w / 2), (p.FLOOR_T, H + 1))
    cavity = fillet(cavity.edges().filter_by(Axis.Z), radius=p.CHASSIS_INNER_CORNER_R)
    shell -= cavity

    for x in (-p.MOTOR_X, p.MOTOR_X):
        for side in (-1, 1):
            wall = sorted((side * (p.MOTOR_FACE_Y - 1), side * (W / 2 + 1)))
            shell -= cylinder((GA25_BOSS_D + 1) / 2, wall, axis="y", at=(x, AXLE_H))
            for dx in (-GA25_FACE_HOLE_SPACING / 2, GA25_FACE_HOLE_SPACING / 2):
                shell -= cylinder(p.M3_CLEARANCE_D / 2, wall, axis="y", at=(x + dx, AXLE_H))

            saddle_y = side * SADDLE_Y
            saddle = box((x - 10, x + 10), (saddle_y - 2, saddle_y + 2), (p.FLOOR_T - 0.1, AXLE_H))
            saddle -= cylinder(
                GA25_CAN_D / 2 + p.FIT_CLEARANCE,
                (saddle_y - 3, saddle_y + 3),
                axis="y",
                at=(x, AXLE_H),
            )
            shell += saddle

    guide_z = (p.FLOOR_T - 0.1, p.FLOOR_T + BATTERY_GUIDE_H)
    battery_size = (LIPO_L + 2 * p.FIT_CLEARANCE + 1, LIPO_W + 2 * p.FIT_CLEARANCE + 1)
    shell += corner_guides(p.BATTERY_CENTER, battery_size, guide_z, leg=15)
    ubec_size = (UBEC_L + 2 * p.FIT_CLEARANCE, UBEC_W + 2 * p.FIT_CLEARANCE)
    shell += corner_guides(
        p.UBEC_CENTER, ubec_size, (p.FLOOR_T - 0.1, p.FLOOR_T + UBEC_GUIDE_H), leg=8
    )

    for x, y in p.DECK_SCREWS:
        shell += cylinder(p.DECK_BOSS_D / 2, (p.FLOOR_T - 0.1, H), at=(x, y))
        shell -= cylinder(p.M3_PILOT_D / 2, (H - DECK_PILOT_DEPTH, H + 1), at=(x, y))

    assert LIPO_H < H - p.FLOOR_T
    assert UBEC_H < H - p.FLOOR_T
    return shell
