"""Deck: the lid of the chassis tray, carrying the electronics and the camera mast.

Screws onto the chassis wall bosses with 4x M3. The Uno and ULN2003 self-tap
onto standoffs (M3). The TB6612 boards (headers soldered pins-up) press into
corner guides. The pan stepper hangs between two pillars, screwed through its
ears (2x M3). Slots let the motor, battery, and UBEC wires up from the tray.

Local frame: the global XY origin, with Z=0 at the deck underside.
Printed as modelled, plate down, with no supports.
"""

from build123d import Axis, Part, fillet

from harwood0_cad import params as p
from harwood0_cad.hardware.boards import (
    TB6612_SIZE,
    ULN2003_HOLE_INSET,
    ULN2003_L,
    ULN2003_W,
    UNO_HOLES,
)
from harwood0_cad.hardware.motors import BYJ_BODY_D, BYJ_EAR_SPACING
from harwood0_cad.shapes import box, corner_guides, cylinder

PILLAR_W = 8.0  # along X
PILLAR_DEPTH = 6.5  # along Y, from the body clearance outward
TB6612_GUIDE_H = 3.0
WIRE_SLOTS = (
    ((-6.0, 6.0), (-35.0, 35.0)),  # centre: battery, UBEC, rear motors
    ((58.0, 66.0), (-12.0, 12.0)),  # front motors
)


def deck() -> Part:
    L, W, T = p.CHASSIS_L, p.CHASSIS_W, p.DECK_T
    plate = box((-L / 2, L / 2), (-W / 2, W / 2), (0, T))
    plate = fillet(plate.edges().filter_by(Axis.Z), radius=p.CHASSIS_CORNER_R)
    for x, y in p.DECK_SCREWS:
        plate -= cylinder(p.M3_CLEARANCE_D / 2, (-1, T + 1), at=(x, y))
    for x, y in WIRE_SLOTS:
        slot = box(x, y, (-1, T + 1))
        plate -= fillet(slot.edges().filter_by(Axis.Z), radius=(x[1] - x[0]) / 2 - 0.01)

    ux, uy = p.UNO_ORIGIN
    board_holes = [(ux + hx, uy + hy) for hx, hy in UNO_HOLES]
    cx, cy = p.ULN2003_CENTER
    ix, iy = ULN2003_L / 2 - ULN2003_HOLE_INSET, ULN2003_W / 2 - ULN2003_HOLE_INSET
    board_holes += [(cx + sx * ix, cy + sy * iy) for sx in (-1, 1) for sy in (-1, 1)]
    for x, y in board_holes:
        plate += cylinder(p.BOARD_STANDOFF_D / 2, (T - 0.1, T + p.UNO_STANDOFF_H), at=(x, y))
        plate -= cylinder(p.M3_PILOT_D / 2, (T, T + p.UNO_STANDOFF_H + 1), at=(x, y))

    tb_size = (TB6612_SIZE + 2 * p.FIT_CLEARANCE, TB6612_SIZE + 2 * p.FIT_CLEARANCE)
    for center in p.TB6612_CENTERS:
        plate += corner_guides(center, tb_size, (T - 0.1, T + TB6612_GUIDE_H), leg=6)

    inner = BYJ_BODY_D / 2 + 0.5
    x0 = p.STEPPER_BODY_X
    for side in (-1, 1):
        y = sorted((side * inner, side * (inner + PILLAR_DEPTH)))
        pillar = box((x0 - PILLAR_W / 2, x0 + PILLAR_W / 2), y, (T - 0.1, T + p.STEPPER_PILLAR_H))
        pillar -= cylinder(
            p.M3_PILOT_D / 2,
            (T + 4, T + p.STEPPER_PILLAR_H + 1),
            at=(x0, side * BYJ_EAR_SPACING / 2),
        )
        plate += pillar
    return plate
