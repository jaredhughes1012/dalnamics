"""Track lip: fills one side of the track's entry pocket after the carriage is in.

Each strip rebuilds one sloped wall of the dovetail, so the carriage can run over
the pocket like the rest of the slot. Print two; on the robot the second is
turned half a turn to fill the other side. Each screws down with 2 screws.

Local frame: global X and Z, with Y measured from the slot centreline; this strip
fills the +Y side. Printed lying on its outer face.
"""

from build123d import Part, Polyline, extrude, make_face

from harwood0_cad import params as p
from harwood0_cad.shapes import cylinder
from harwood0_cad.track_geometry import (
    ENTRY_L,
    LIP_SCREW_INSET,
    LIP_SCREW_Y,
    POCKET_HALF_W,
    SLOT_BOTTOM_W,
    SLOT_FLOOR_Z,
    SLOT_TOP_W,
    TRACK_T,
)

LIP_CLEARANCE = 0.2


def track_lip() -> Part:
    c = LIP_CLEARANCE
    length = ENTRY_L - 2 * c
    profile = Polyline(
        (0, SLOT_BOTTOM_W / 2, SLOT_FLOOR_Z),
        (0, POCKET_HALF_W - c, SLOT_FLOOR_Z),
        (0, POCKET_HALF_W - c, TRACK_T),
        (0, SLOT_TOP_W / 2, TRACK_T),
        close=True,
    )
    lip = extrude(make_face(profile), amount=length, dir=(1, 0, 0))
    for x in (LIP_SCREW_INSET - c, length - LIP_SCREW_INSET + c):
        lip -= cylinder(
            p.STRUCTURAL_SCREW.clearance_d / 2, (SLOT_FLOOR_Z - 1, TRACK_T + 1), at=(x, LIP_SCREW_Y)
        )
        head_z = (
            TRACK_T - p.STRUCTURAL_SCREW.head_h - 0.3,
            TRACK_T + 1,
        )  # the head sits below the top
        lip -= cylinder(p.STRUCTURAL_SCREW.head_d / 2 + 0.2, head_z, at=(x, LIP_SCREW_Y))
    return lip
