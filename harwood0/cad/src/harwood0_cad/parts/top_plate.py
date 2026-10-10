"""Top plate: closes the chassis, carries the track, and frames the work table.

The plate snaps onto the chassis: press it down until the snap arms' barbs click
over its top face; push the barbs inwards to lift it off.

The arm tower's ribbon cable lies in the channel recessed into the margin between
the track and the table, and drops into the body through the port at its front end. A margin of plate shows all
the way round the table, giving the cameras a clear boundary to the work surface.
The table drops into the opening and rests on a lip, flush with the top.

The track is a raised strip along the right-hand side. The carriage's dovetail
runners slide in its dovetail slot, which locates the carriage sideways and stops
it lifting. A gear rack runs along the slot floor for the carriage's pinion.

At the slot's rear end is an entry pocket with straight walls: lower the carriage
in there and slide it forward, then drop the two lip strips into the pocket and
screw them down (2 screws each, into inserts) to rebuild the dovetail. Both ends of the slot are
closed, so they are the carriage's end stops.

Local frame: the global XY origin, with Z=0 at the plate underside.
Printed flat, underside down; the dovetail's sloped walls print without supports.
"""

import math

from build123d import Axis, Part, Polyline, extrude, fillet, make_face

from harwood0_cad import params as p
from harwood0_cad.parts.body import body_plan
from harwood0_cad.parts.fasteners import insert_hole
from harwood0_cad.parts.snaps import snap_slots
from harwood0_cad.shapes import box, cylinder
from harwood0_cad.track_geometry import (
    LIP_SCREW_INSET,
    LIP_SCREW_Y,
    POCKET_HALF_W,
    POCKET_X,
    RACK_FACE_W,
    RACK_MODULE,
    RACK_PITCH_Z,
    RACK_PRESSURE_ANGLE,
    SLOT_BOTTOM_W,
    SLOT_FLOOR_Z,
    SLOT_TOP_W,
    SLOT_X,
    SLOT_Y,
    TRACK_T,
)

PLATE_T = p.TOP_PLATE_T
LIP_T = p.TOP_PLATE_T - p.TABLE_T  # the lip the table rests on
TABLE_CLEARANCE = 0.4


def table_outline(inset: float, z: tuple[float, float]) -> Part:
    """The table's plan shape grown by `inset` (negative shrinks it), over `z`."""
    plan = body_plan(p.TABLE_MARGIN - inset, z)
    return plan & box(
        (-p.CHASSIS_L, p.CHASSIS_L), (p.TABLE_Y[0] - inset, p.CHASSIS_W), (z[0] - 1, z[1] + 1)
    )


def _dovetail(x: tuple[float, float]) -> Part:
    top, bottom = SLOT_TOP_W / 2, SLOT_BOTTOM_W / 2
    profile = Polyline(
        (x[0], SLOT_Y - bottom, SLOT_FLOOR_Z),
        (x[0], SLOT_Y + bottom, SLOT_FLOOR_Z),
        (x[0], SLOT_Y + top, TRACK_T + 0.01),
        (x[0], SLOT_Y - top, TRACK_T + 0.01),
        close=True,
    )
    return extrude(make_face(profile), amount=x[1] - x[0], dir=(1, 0, 0))


def _rack(x: tuple[float, float]) -> Part:
    m = RACK_MODULE
    pitch = math.pi * m
    tan = math.tan(math.radians(RACK_PRESSURE_ANGLE))
    root_half = pitch / 4 + 1.25 * m * tan
    tip_half = pitch / 4 - m * tan
    y = (SLOT_Y - RACK_FACE_W / 2, SLOT_Y + RACK_FACE_W / 2)
    teeth = None
    for i in range(int((x[1] - x[0]) / pitch)):
        cx = x[0] + pitch * (i + 0.5)
        profile = Polyline(
            (cx - root_half, y[0], SLOT_FLOOR_Z - 0.01),
            (cx + root_half, y[0], SLOT_FLOOR_Z - 0.01),
            (cx + tip_half, y[0], RACK_PITCH_Z + m),
            (cx - tip_half, y[0], RACK_PITCH_Z + m),
            close=True,
        )
        tooth = extrude(make_face(profile), amount=y[1] - y[0], dir=(0, 1, 0))
        teeth = tooth if teeth is None else teeth + tooth
    return teeth


def top_plate() -> Part:
    plate = body_plan(0, (0, PLATE_T))
    plate -= table_outline(TABLE_CLEARANCE, (LIP_T, PLATE_T + 1))
    plate -= table_outline(TABLE_CLEARANCE - p.TABLE_LIP_W, (-1, LIP_T + 0.01))

    plate += box(p.TRACK_X, p.TRACK_Y, (PLATE_T - 0.1, TRACK_T))
    plate -= _dovetail(SLOT_X)
    plate -= box(
        POCKET_X, (SLOT_Y - POCKET_HALF_W, SLOT_Y + POCKET_HALF_W), (SLOT_FLOOR_Z, TRACK_T + 1)
    )
    plate += _rack(SLOT_X)
    for x in (POCKET_X[0] + LIP_SCREW_INSET, POCKET_X[1] - LIP_SCREW_INSET):
        for y in (SLOT_Y - LIP_SCREW_Y, SLOT_Y + LIP_SCREW_Y):
            # Inserts pressed in from the pocket floor, on bosses under the plate.
            boss_z = (SLOT_FLOOR_Z - p.INSERT_DEPTH, 0.1)
            plate += cylinder(p.INSERT_BOSS_D / 2, boss_z, at=(x, y))
            plate -= insert_hole(SLOT_FLOOR_Z, -1, (x, y))

    plate -= snap_slots()

    y0, y1 = p.CABLE_CHANNEL_Y
    plate -= box(p.CABLE_CHANNEL_X, (y0, y1), (PLATE_T - p.CABLE_CHANNEL_DEPTH, PLATE_T + 1))
    port = box(p.CABLE_PORT_X, (y0, y1), (-1, PLATE_T + 1))
    return plate - fillet(port.edges().filter_by(Axis.Z), radius=(y1 - y0) / 2 - 0.01)
