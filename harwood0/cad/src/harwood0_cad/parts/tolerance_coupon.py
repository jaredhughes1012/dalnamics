"""A test print for calibrating hole fits before printing body parts.

Three rows of holes, each stepping through diameters around one of the sizes the
robot's screws use. Each row is marked by grooves engraved at its small end:

- 1 groove: M2.5 self-tapping pilot (M2_5_PILOT_D), for the servo driver.
- 2 grooves: M3 self-tapping pilot (M3_PILOT_D), for almost every other screw.
- 3 grooves: M3 clearance (M3_CLEARANCE_D, set by FIT_CLEARANCE), for the holes screws pass through.

Holes step up by HOLE_STEP from the grooved end; the middle hole of each row is the
current size. Drive a screw into each pilot hole and pick the one it grips firmly
without splitting or needing force; push an M3 screw through the clearance holes and
pick the smallest it passes freely. Then shift the matching value in params.py by
HOLE_STEP for each hole away from the middle, and re-export.

Printed flat, as modelled.
"""

from build123d import Axis, Part, fillet

from harwood0_cad import params as p
from harwood0_cad.shapes import box, cylinder

HOLE_STEP = 0.1
HOLE_COUNT = 5
PITCH = 9.0
THICKNESS = 6.0
MARK_W = 9.0  # space at the left end of each row for its grooves
GROOVE_W = 0.8
GROOVE_PITCH = 1.8
GROOVE_DEPTH = 0.6
GROOVE_L = 5.0

ROWS = (p.M2_5_PILOT_D, p.M3_PILOT_D, p.M3_CLEARANCE_D)  # from the back row to the front


def hole_diameters(nominal: float) -> list[float]:
    offset = (HOLE_COUNT - 1) / 2
    return [round(nominal + (i - offset) * HOLE_STEP, 2) for i in range(HOLE_COUNT)]


def tolerance_coupon() -> Part:
    length = MARK_W + PITCH * HOLE_COUNT
    width = PITCH * len(ROWS) + 2.0
    x0 = -length / 2
    coupon = box((x0, length / 2), (-width / 2, width / 2), (0, THICKNESS))
    coupon = fillet(coupon.edges().filter_by(Axis.Z), radius=2.0)

    for row, nominal in enumerate(ROWS):
        y = ((len(ROWS) - 1) / 2 - row) * PITCH
        for col, diameter in enumerate(hole_diameters(nominal)):
            x = x0 + MARK_W + PITCH * (col + 0.5)
            coupon -= cylinder(diameter / 2, (-1, THICKNESS + 1), at=(x, y))
        for i in range(row + 1):
            gx = x0 + 2.5 + i * GROOVE_PITCH
            coupon -= box(
                (gx, gx + GROOVE_W),
                (y - GROOVE_L / 2, y + GROOVE_L / 2),
                (THICKNESS - GROOVE_DEPTH, THICKNESS + 1),
            )
    return coupon
