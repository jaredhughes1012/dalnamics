"""Work table: a flat plate that drops into the top plate's opening.

It rests on a lip around the opening, flush with the body top, with nothing to
unscrew; lift it by the finger notch at the rear to reach the electronics. A
margin of top plate shows all round it. Its outline follows the body's rounded
corners.

Local frame: the global XY origin, with Z=0 at the table underside.
Printed flat.
"""

from build123d import Part

from harwood0_cad import params as p
from harwood0_cad.parts.top_plate import table_outline
from harwood0_cad.shapes import cylinder

FINGER_NOTCH_R = 11.0


def table() -> Part:
    plate = table_outline(0, (0, p.TABLE_T))
    notch_x = -p.CHASSIS_L / 2 + p.TABLE_MARGIN
    notch_y = sum(p.TABLE_Y) / 2
    return plate - cylinder(FINGER_NOTCH_R, (-1, p.TABLE_T + 1), at=(notch_x, notch_y))
