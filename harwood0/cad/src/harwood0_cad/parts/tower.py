"""Arm tower: the column (with the servo driver inside), the hood on top, the hood's lid,
and the column's access door.

The column's flange screws onto the carriage deck (4x M3). The PCA9685 servo
driver screws to the inside of the column's inboard wall on short bosses (4x
M2.5 self-tapping), its headers facing the access door in the outboard wall.

The hood screws onto the column's top (4x M3, driven down through the hood floor
into corner blocks in the column), so each prints without supports. The yaw
servo pushes up into the hood from below, shaft down, and screws to the hood floor
by its tabs (4x M3). The lid snaps onto the hood: push its four barbs inwards to
lift it off.

The door hooks into the bottom of its opening by two hooks, then two springy
tongues at its top click their barbs behind the opening's sides. Squeeze the
tongues towards the middle to open it.

Wiring: the arm's leads (shoulder, elbow, gripper, arm camera) come up from the
yaw bracket through the cable hole at the front of the hood floor. They and the
yaw servo's lead drop through the opening in the hood floor into the column, to
the servo driver. The bundle back to the body (I2C, servo power, and the track
stepper) leaves through the column's open base into the carriage.

Local frame: the tower frame (origin at the carriage centre on the track's top face).
Column: printed upright on its flange. Hood: printed floor down. Lid: printed
underside down, its rounded edges up. Door: printed flat, outer face down.
"""

from build123d import (
    Axis,
    Location,
    Part,
    Plane,
    Polyline,
    Pos,
    RectangleRounded,
    Rot,
    extrude,
    fillet,
    loft,
    make_face,
)

from harwood0_cad import params as p
from harwood0_cad.arm_geometry import (
    CARRIAGE_DECK_Z,
    CARRIAGE_HALF_L,
    CARRIAGE_SCREWS,
    CARRIAGE_Y,
    HOOD_FLOOR_Z,
    YAW_SERVO_FACE_Z,
    YAW_Y,
)
from harwood0_cad.hardware.boards import PCA9685_HOLE_INSET, PCA9685_L, PCA9685_W
from harwood0_cad.hardware.motors import (
    STD_SERVO_BODY_H,
    STD_SERVO_BODY_L,
    STD_SERVO_BODY_W,
    STD_SERVO_SHAFT_OFFSET,
    STD_SERVO_TAB_HOLES,
)
from harwood0_cad.parts.snaps import snap_arms, snap_slots
from harwood0_cad.shapes import box, cylinder

FLANGE_T = 4.0
COLUMN_WALL = 2.4
# The column tapers side to side; its inboard face stays clear of the yaw bracket's and the arm's
# swing, and its outboard face (with the door) is vertical. Deep enough for the servo driver with
# its plugs fitted, plus the arm's bundled leads running down in front of them.
COLUMN_BASE = ((-18.0, 18.0), (-23.0, 14.0))  # X and Y spans where the column meets the flange
COLUMN_TOP = ((-16.0, 16.0), (-23.0, 14.0))  # and where it meets the hood
COLUMN_R = 4.0
COLUMN_INBOARD_FACE = COLUMN_TOP[1][1] - COLUMN_WALL  # inside face of the inboard wall
COLUMN_OUTBOARD = COLUMN_TOP[1][0]  # outside face of the outboard wall

# Hood-to-column joint: corner blocks at the top of the column take the hood's screws.
JOINT_BLOCK = 7.0
JOINT_BLOCK_H = 12.0
JOINT_PILOT_DEPTH = 10.0
_IX = COLUMN_TOP[0][1] - COLUMN_WALL  # column interior half-width at the top
HOOD_SCREWS = tuple(
    (sx * (_IX - JOINT_BLOCK / 2), y)
    for sx in (-1, 1)
    for y in (
        COLUMN_OUTBOARD + COLUMN_WALL + JOINT_BLOCK / 2,
        COLUMN_INBOARD_FACE - JOINT_BLOCK / 2,
    )
)
COLUMN_PASS = (
    (-12.0, 12.0),
    (COLUMN_OUTBOARD + COLUMN_WALL + JOINT_BLOCK + 0.5, COLUMN_INBOARD_FACE - JOINT_BLOCK - 0.5),
)

HOOD_X = 16.0
HOOD_Y = (COLUMN_OUTBOARD, YAW_Y + 28.0)  # long enough for the arm cable hole beyond the yaw servo
HOOD_WALL = 3.0
HOOD_FLOOR_T = 3.5
HOOD_TOP_Z = YAW_SERVO_FACE_Z + STD_SERVO_BODY_H + 6.0
HOOD_FRONT_R = 10.0
LID_T = 3.0
LID_Z = HOOD_TOP_Z - LID_T  # lid underside, where the hood's walls end
LID_EDGE_R = 2.0
TAB_BOSS_D = 7.0
TAB_BOSS_H = 6.0
YAW_SERVO_BODY_Y = YAW_Y - STD_SERVO_SHAFT_OFFSET  # body centre, towards the column

# The lid's snap arms, on the hood's side walls clear of the yaw servo: one pair over the
# column and one pair near the front.
HOOD_SNAPS = tuple(
    ((side * (HOOD_X - HOOD_WALL), y), 180.0 if side > 0 else 0.0)
    for side in (-1, 1)
    for y in (4.0, YAW_Y + 15.0)
)

# Arm cable hole in the hood floor, past the yaw servo's tab bosses.
ARM_CABLE_HOLE = ((-8.0, 8.0), (YAW_SERVO_BODY_Y + 29.0, HOOD_Y[1] - HOOD_WALL - 0.5))

# Servo driver: inside the column on its inboard wall, long axis vertical, components
# facing the door. Its bosses stand it just off the wall so the screws have something to bite.
DRIVER_CENTER_Z = 98.0
DRIVER_BOSS_D = 5.0
DRIVER_BOSS_H = 2.5
DRIVER_PCB_Y = COLUMN_INBOARD_FACE - DRIVER_BOSS_H  # the board's back face
# Where the board sits: its long axis vertical, components facing the door (-Y).
DRIVER_PLACE: Location = Pos(0, DRIVER_PCB_Y, DRIVER_CENTER_Z) * Rot(0, 0, 90) * Rot(0, -90, 0)
DRIVER_SERVO_CHANNELS = 5  # four arm servos, and the arm camera's power from channel 4's V+ and GND

# Access door in the outboard wall, in front of the servo driver.
DOOR_OPENING = ((-11.0, 11.0), (DRIVER_CENTER_Z - 38.0, DRIVER_CENTER_Z + 38.0))  # X and Z spans
DOOR_OVERLAP = 3.0
DOOR_T = COLUMN_WALL
DOOR_HOOK_X = (4.0, 9.0)  # each bottom hook's span either side of centre
TONGUE_X = (7.0, 9.0)  # each top tongue's span either side of centre
TONGUE_L = 16.0
TONGUE_SLOT = 1.2
BARB = 1.2  # how far each tongue's barb reaches behind the opening's side
DOOR_CLEARANCE = 0.2


def _section(span: tuple[tuple[float, float], tuple[float, float]], z: float, inset: float = 0.0):
    (x0, x1), (y0, y1) = span
    w, h = x1 - x0 - 2 * inset, y1 - y0 - 2 * inset
    return (
        Plane.XY.offset(z)
        * Pos((x0 + x1) / 2, (y0 + y1) / 2)
        * RectangleRounded(w, h, max(COLUMN_R - inset, 0.5))
    )


def _hood_plan(inset: float, z: tuple[float, float]) -> Part:
    """The hood's outline shrunk by `inset`, rounded at the front, over `z`."""
    plan = box((-HOOD_X + inset, HOOD_X - inset), (HOOD_Y[0] + inset, HOOD_Y[1] - inset), z)
    front = (
        plan.edges().filter_by(Axis.Z).filter_by_position(Axis.Y, HOOD_Y[1] - inset - 1, HOOD_Y[1])
    )
    return fillet(front, HOOD_FRONT_R - inset)


def tower() -> Part:
    """The column, from the flange on the carriage to the hood joint at its top."""
    flange_z = (CARRIAGE_DECK_Z[1], CARRIAGE_DECK_Z[1] + FLANGE_T)
    flange_y = (
        min(CARRIAGE_Y[0], COLUMN_OUTBOARD),
        CARRIAGE_Y[1],
    )  # out to the column's outboard face
    body = box((-CARRIAGE_HALF_L, CARRIAGE_HALF_L), flange_y, flange_z)
    for x, y in CARRIAGE_SCREWS:
        body -= cylinder(p.M3_CLEARANCE_D / 2, (flange_z[0] - 1, flange_z[1] + 1), at=(x, y))

    top = HOOD_FLOOR_Z
    body += loft([_section(COLUMN_BASE, flange_z[1] - 0.1), _section(COLUMN_TOP, top)])
    body -= loft(
        [
            _section(COLUMN_BASE, flange_z[0] - 1, COLUMN_WALL),
            _section(COLUMN_TOP, top + 1, COLUMN_WALL),
        ]
    )

    # Corner blocks for the hood's screws.
    for x, y in HOOD_SCREWS:
        half = JOINT_BLOCK / 2
        block = box((x - half, x + half), (y - half, y + half), (top - JOINT_BLOCK_H, top))
        body += block - cylinder(p.M3_PILOT_D / 2, (top - JOINT_PILOT_DEPTH, top + 1), at=(x, y))

    # Servo driver bosses on the inside of the inboard wall.
    hz, hx = PCA9685_L / 2 - PCA9685_HOLE_INSET, PCA9685_W / 2 - PCA9685_HOLE_INSET
    for dz in (-hz, hz):
        for x in (-hx, hx):
            at = (x, DRIVER_CENTER_Z + dz)
            body += cylinder(
                DRIVER_BOSS_D / 2, (DRIVER_PCB_Y, COLUMN_INBOARD_FACE + 0.5), axis="y", at=at
            )
            body -= cylinder(
                p.M2_5_PILOT_D / 2,
                (DRIVER_PCB_Y - 1, COLUMN_INBOARD_FACE + COLUMN_WALL - 0.5),
                axis="y",
                at=at,
            )

    (ox0, ox1), (oz0, oz1) = DOOR_OPENING
    return body - box(
        (ox0, ox1), (COLUMN_OUTBOARD - 1, COLUMN_OUTBOARD + COLUMN_WALL + 1), (oz0, oz1)
    )


def hood() -> Part:
    """The hood: screws onto the column, carries the yaw servo, and takes the lid."""
    floor_top = HOOD_FLOOR_Z + HOOD_FLOOR_T
    body = _hood_plan(0, (HOOD_FLOOR_Z, LID_Z))
    body -= _hood_plan(HOOD_WALL, (floor_top, LID_Z + 1))
    body += snap_arms(LID_Z, HOOD_SNAPS, LID_T)

    # Yaw servo: through a window in the floor, tabs screwed up into bosses.
    c = p.FIT_CLEARANCE
    hl, hw = STD_SERVO_BODY_L / 2 + c, STD_SERVO_BODY_W / 2 + c
    along, across = STD_SERVO_TAB_HOLES
    for dy in (-along / 2, along / 2):
        for x in (-across / 2, across / 2):
            at = (x, YAW_SERVO_BODY_Y + dy)
            body += cylinder(TAB_BOSS_D / 2, (floor_top - 0.1, floor_top + TAB_BOSS_H), at=at)
            body -= cylinder(
                p.M3_PILOT_D / 2, (HOOD_FLOOR_Z - 1, floor_top + TAB_BOSS_H - 1), at=at
            )
    floor_z = (HOOD_FLOOR_Z - 1, floor_top + 1)
    body -= box((-hw, hw), (YAW_SERVO_BODY_Y - hl, YAW_SERVO_BODY_Y + hl), floor_z)

    # Wire openings: the arm's leads come up through the cable hole, and everything drops
    # into the column through the pass.
    body -= box(*ARM_CABLE_HOLE, floor_z)
    body -= box(*COLUMN_PASS, floor_z)
    for x, y in HOOD_SCREWS:
        body -= cylinder(p.M3_CLEARANCE_D / 2, floor_z, at=(x, y))
    return body


def hood_lid() -> Part:
    """The hood's lid: snaps on, and lifts off for routing wires in the hood and column."""
    lid = _hood_plan(0, (LID_Z, HOOD_TOP_Z))
    lid = fillet(
        lid.edges().filter_by_position(Axis.Z, HOOD_TOP_Z - 0.1, HOOD_TOP_Z + 0.1), LID_EDGE_R
    )
    return lid - snap_slots(HOOD_SNAPS, LID_T, LID_Z)


def _door_barb(side: int, z: tuple[float, float]) -> Part:
    """A barb on a tongue's inner face, reaching through the opening and behind its side.

    Its leading face is ramped, so the opening's side pushes the tongue inwards as the door
    closes; once past the wall it springs out and catches behind it.
    """
    inner = COLUMN_OUTBOARD + COLUMN_WALL + DOOR_CLEARANCE  # just behind the wall
    edge = DOOR_OPENING[0][1] - DOOR_CLEARANCE
    x0 = TONGUE_X[0]
    profile = Polyline(
        (side * x0, COLUMN_OUTBOARD, z[0]),
        (side * edge, COLUMN_OUTBOARD, z[0]),
        (side * edge, inner, z[0]),
        (side * (edge + BARB), inner, z[0]),
        (side * edge, inner + 1.0, z[0]),
        (side * x0, inner + 1.0, z[0]),
        close=True,
    )
    return extrude(make_face(profile), amount=z[1] - z[0], dir=(0, 0, 1))


def tower_door() -> Part:
    """The access door over the servo driver."""
    (ox0, ox1), (oz0, oz1) = DOOR_OPENING
    o = DOOR_OVERLAP
    y = (COLUMN_OUTBOARD - DOOR_T, COLUMN_OUTBOARD)
    door = box((ox0 - o, ox1 + o), y, (oz0 - o, oz1 + o))

    # Bottom hooks: through the opening, then down behind the wall below it.
    behind = (COLUMN_OUTBOARD + COLUMN_WALL + DOOR_CLEARANCE, COLUMN_OUTBOARD + COLUMN_WALL + 1.2)
    for sx in (-1, 1):
        hx = sorted((sx * DOOR_HOOK_X[0], sx * DOOR_HOOK_X[1]))
        door += box(hx, (y[1] - 0.1, behind[1]), (oz0 + DOOR_CLEARANCE, oz0 + 4.0))
        door += box(hx, behind, (oz0 - 3.0, oz0 + 4.0))

    # Top tongues: slotted free from the door so they flex sideways, each with a barb.
    tip = oz1 - 2.0
    for sx in (-1, 1):
        tx = sorted((sx * TONGUE_X[0], sx * TONGUE_X[1]))
        s = TONGUE_SLOT
        door -= box((tx[0] - s, tx[0]), (y[0] - 1, y[1] + 1), (tip - TONGUE_L, tip + s))
        door -= box((tx[1], tx[1] + s), (y[0] - 1, y[1] + 1), (tip - TONGUE_L, tip + s))
        door -= box((tx[0] - s, tx[1] + s), (y[0] - 1, y[1] + 1), (tip, tip + s))
        door += _door_barb(sx, (tip - 6.0, tip))
    return door
