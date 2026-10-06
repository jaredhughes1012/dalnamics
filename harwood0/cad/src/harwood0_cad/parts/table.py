"""Work table: a flat plate that drops into the top plate's opening.

It rests on a lip around the opening, flush with the body top, with nothing to
unscrew; lift it by the finger notch at the rear to reach the electronics. A
margin of top plate shows all round it. Its outline follows the body's rounded
corners.

A low rim, inset from the edges and clear of the notch, keeps objects the arm
places on the table from sliding off while the rover moves.

Local frame: the global XY origin, with Z=0 at the table underside.
Printed flat.
"""

from build123d import Part, Pos, RectangleRounded, extrude

from harwood0_cad import params as p
from harwood0_cad.parts.top_plate import table_outline
from harwood0_cad.shapes import cylinder

FINGER_NOTCH_R = 11.0
NOTCH_X = -p.CHASSIS_L / 2 + p.TABLE_MARGIN

# The rim's outer edge, in plan.
RIM_X = (
    NOTCH_X + FINGER_NOTCH_R + p.TABLE_RIM_INSET,
    p.CHASSIS_L / 2 - p.TABLE_MARGIN - p.TABLE_RIM_INSET,
)
RIM_Y = (p.TABLE_Y[0] + p.TABLE_RIM_INSET, p.TABLE_Y[1] - p.TABLE_RIM_INSET)


def _rounded_rect(inset: float, z: tuple[float, float]) -> Part:
    w, h = RIM_X[1] - RIM_X[0] - 2 * inset, RIM_Y[1] - RIM_Y[0] - 2 * inset
    face = RectangleRounded(w, h, p.TABLE_RIM_R - inset)
    center = Pos(sum(RIM_X) / 2, sum(RIM_Y) / 2, z[0])
    return center * extrude(face, z[1] - z[0])


def rim() -> Part:
    z = (p.TABLE_T - 0.01, p.TABLE_T + p.TABLE_RIM_H)
    return _rounded_rect(0, z) - _rounded_rect(p.TABLE_RIM_W, (z[0] - 1, z[1] + 1))


def table() -> Part:
    plate = table_outline(0, (0, p.TABLE_T))
    notch_y = sum(p.TABLE_Y) / 2
    plate -= cylinder(FINGER_NOTCH_R, (-1, p.TABLE_T + 1), at=(NOTCH_X, notch_y))
    return plate + rim()
