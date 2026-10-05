"""A test print for calibrating hole fits before printing body parts.

A row of holes steps through diameters around the nominal M3 clearance and
heat-set insert sizes. Print it, test fasteners and inserts, then set
FIT_CLEARANCE and M3_HEAT_SET_D in params.py to the sizes that fit.
"""

from build123d import Axis, Box, BuildPart, Hole, Locations, Part, fillet

from harwood0_cad import params

HOLE_STEP = 0.1
HOLE_COUNT = 5
PITCH = 9.0
THICKNESS = 6.0


def _hole_diameters(nominal: float) -> list[float]:
    offset = (HOLE_COUNT - 1) / 2
    return [round(nominal + (i - offset) * HOLE_STEP, 2) for i in range(HOLE_COUNT)]


def tolerance_coupon() -> Part:
    rows = [_hole_diameters(params.M3_CLEARANCE_D), _hole_diameters(params.M3_HEAT_SET_D)]
    length = PITCH * (HOLE_COUNT + 1)
    width = PITCH * (len(rows) + 1)

    with BuildPart() as coupon:
        Box(length, width, THICKNESS)
        fillet(coupon.edges().filter_by(Axis.Z), radius=2.0)
        for row_index, diameters in enumerate(rows):
            y = (row_index - (len(rows) - 1) / 2) * PITCH
            for col_index, diameter in enumerate(diameters):
                x = (col_index - (HOLE_COUNT - 1) / 2) * PITCH
                with Locations((x, y, THICKNESS / 2)):
                    Hole(radius=diameter / 2)

    return coupon.part
