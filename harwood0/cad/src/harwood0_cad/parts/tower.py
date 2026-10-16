"""Arm tower: the column (with the servo driver inside), the hood on top, the hood's lid,
and the column's access door.

The column's flange screws onto the carriage deck (4 screws). The PCA9685 servo
driver screws to the inside of the column's inboard wall on short bosses (4 screws
into heat-set inserts), its headers facing the access door in the outboard wall.

The hood screws onto the column's top (4 screws, driven down through the hood floor
into inserts in corner blocks in the column), so each prints without supports. The yaw
servo pushes up into the hood from below, shaft down, its lead through the notch at the
front end of its window. Its tabs bolt to the hood floor: 4 screws up from below, into
nuts dropped into the pockets on top of the bosses. The lid snaps onto the hood: push
its four barbs inwards to lift it off.

The door hooks into the top of its opening by two hooks, then swings shut at the
bottom, where two snap arms standing up inside the column push their barbs out
through slots in the door and click over its outer face, as on the hood lid.
Push the two barbs towards the middle and swing the door's bottom out to open it.

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
    STD_SERVO_LEAD_REACH,
    STD_SERVO_LEAD_W,
    STD_SERVO_SHAFT_OFFSET,
    STD_SERVO_TAB_HOLES,
)
from harwood0_cad.parts.fasteners import insert_hole, nut_corner_r, nut_pocket
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

# Hood-to-column joint: corner blocks at the top of the column take the hood's screws. Wide
# enough to set each screw's head clear of the hood's walls at M3.
JOINT_BLOCK = 7.4
JOINT_BLOCK_H = 12.0
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
TAB_BOSS_D = 2 * (
    nut_corner_r(p.STRUCTURAL_SCREW) + 0.9
)  # round the nut pockets, just clear of the servo body
TAB_BOSS_H = 3.0
YAW_SERVO_BODY_Y = YAW_Y - STD_SERVO_SHAFT_OFFSET  # body centre, towards the column

# The lid's snap arms, on the hood's side walls clear of the yaw servo: one pair over the
# column, between the hood screws so a driver reaches them straight down, and one pair near
# the front.
HOOD_SNAPS = tuple(
    ((side * (HOOD_X - HOOD_WALL), y), 180.0 if side > 0 else 0.0)
    for side in (-1, 1)
    for y in (-4.5, YAW_Y + 15.0)
)

# Arm cable hole in the hood floor, past the yaw servo's tab bosses.
ARM_CABLE_HOLE = ((-8.0, 8.0), (YAW_SERVO_BODY_Y + 29.0, HOOD_Y[1] - HOOD_WALL - 0.5))

# Servo driver: inside the column on its inboard wall, long axis vertical, components
# facing the door. Its bosses stand it just off the wall so the screws have something to bite.
DRIVER_CENTER_Z = 98.0
DRIVER_BOSS_D = p.PCA9685_SCREW.insert_boss_d
DRIVER_BOSS_H = 2.5
DRIVER_PCB_Y = COLUMN_INBOARD_FACE - DRIVER_BOSS_H  # the board's back face
# Where the board sits: its long axis vertical, components facing the door (-Y).
DRIVER_PLACE: Location = Pos(0, DRIVER_PCB_Y, DRIVER_CENTER_Z) * Rot(0, 0, 90) * Rot(0, -90, 0)
DRIVER_SERVO_CHANNELS = 5  # four arm servos, and the arm camera's power from channel 4's V+ and GND

# Access door in the outboard wall, in front of the servo driver.
DOOR_OPENING = ((-11.0, 11.0), (DRIVER_CENTER_Z - 38.0, DRIVER_CENTER_Z + 38.0))  # X and Z spans
DOOR_OVERLAP = 3.0
DOOR_T = COLUMN_WALL
DOOR_HOOK_X = (2.0, 6.0)  # each top hook's span either side of centre
DOOR_CLEARANCE = 0.2
# Each top hook's leg stands up behind the wall above the opening. Its front face leans back
# from the wall towards its foot, so the hung door can swing its bottom out far enough to
# clear the latch barbs; at the top it sits close to the wall, holding the closed door snug.
DOOR_HOOK_LEG_T = 2.0  # from the wall's inside face to the leg's back
DOOR_HOOK_LEG_H = 3.0  # above the opening
DOOR_HOOK_TAPER = 0.6  # extra room at the leg's foot

# The door's latch: an arm each side, standing up inside the column against the outboard wall
# from a root below the opening. Its barb reaches out through a slot in the door and hooks
# over the door's outer face, away from the middle; pushed towards the middle, it lets go.
LATCH_X = (8.0, 10.0)  # each arm's span either side of centre; it flexes towards the middle
LATCH_Y = (COLUMN_OUTBOARD + COLUMN_WALL + 0.3, COLUMN_OUTBOARD + COLUMN_WALL + 4.3)
LATCH_ROOT_Z = (DOOR_OPENING[1][0] - 12.0, DOOR_OPENING[1][0] - 7.0)
LATCH_BARB_Z = DOOR_OPENING[1][0] + 2.0  # where the barb's chamfered underside starts
LATCH_TOP_Z = LATCH_BARB_Z + 12.0
LATCH_BARB = 1.0  # how far the barb hooks over the door's outer face
LATCH_BARB_OUT = 1.5  # how far the barb's tip stands proud of the door, to press on
LATCH_FLEX = 1.5  # room in the door's slot for the arm to flex towards the middle


def _section(span: tuple[tuple[float, float], tuple[float, float]], z: float, inset: float = 0.0):
    (x0, x1), (y0, y1) = span
    w, h = x1 - x0 - 2 * inset, y1 - y0 - 2 * inset
    return (
        Plane.XY.offset(z)
        * Pos((x0 + x1) / 2, (y0 + y1) / 2)
        * RectangleRounded(w, h, max(COLUMN_R - inset, 0.5))
    )


def _hood_plan(inset: float, z: tuple[float, float]) -> Part:
    """The hood's outline shrunk by `inset`, over `z`. Rounded at the front, and at the back
    to match the column's corners where the two meet."""
    plan = box((-HOOD_X + inset, HOOD_X - inset), (HOOD_Y[0] + inset, HOOD_Y[1] - inset), z)

    def corners(y: tuple[float, float]):
        return plan.edges().filter_by(Axis.Z).filter_by_position(Axis.Y, *y)

    plan = fillet(corners((HOOD_Y[1] - inset - 1, HOOD_Y[1])), HOOD_FRONT_R - inset)
    return fillet(corners((HOOD_Y[0], HOOD_Y[0] + inset + 1)), max(COLUMN_R - inset, 0.5))


def tower() -> Part:
    """The column, from the flange on the carriage to the hood joint at its top."""
    flange_z = (CARRIAGE_DECK_Z[1], CARRIAGE_DECK_Z[1] + FLANGE_T)
    flange_y = (
        min(CARRIAGE_Y[0], COLUMN_OUTBOARD),
        CARRIAGE_Y[1],
    )  # out to the column's outboard face
    body = box((-CARRIAGE_HALF_L, CARRIAGE_HALF_L), flange_y, flange_z)
    for x, y in CARRIAGE_SCREWS:
        body -= cylinder(
            p.STRUCTURAL_SCREW.clearance_d / 2, (flange_z[0] - 1, flange_z[1] + 1), at=(x, y)
        )

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
        body += block - insert_hole(p.STRUCTURAL_SCREW, top, -1, (x, y))

    # Servo driver bosses on the inside of the inboard wall.
    hz, hx = PCA9685_L / 2 - PCA9685_HOLE_INSET, PCA9685_W / 2 - PCA9685_HOLE_INSET
    for dz in (-hz, hz):
        for x in (-hx, hx):
            at = (x, DRIVER_CENTER_Z + dz)
            body += cylinder(
                DRIVER_BOSS_D / 2, (DRIVER_PCB_Y, COLUMN_INBOARD_FACE + 0.5), axis="y", at=at
            )
            # Through the wall: the insert goes in from the board's side.
            through = COLUMN_INBOARD_FACE + COLUMN_WALL + 1 - DRIVER_PCB_Y
            body -= insert_hole(p.PCA9685_SCREW, DRIVER_PCB_Y, 1, at, axis="y", depth=through)

    (ox0, ox1), (oz0, oz1) = DOOR_OPENING
    body -= box((ox0, ox1), (COLUMN_OUTBOARD - 1, COLUMN_OUTBOARD + COLUMN_WALL + 1), (oz0, oz1))
    for side in (-1, 1):
        body += _latch_arm(side)
    return body


def _yz_prism(points: list[tuple[float, float]], x: tuple[float, float]) -> Part:
    """A prism with a YZ-plane profile through `points`, spanning `x`."""
    profile = Polyline(*[(x[0], y, z) for y, z in points], close=True)
    return extrude(make_face(profile), amount=x[1] - x[0], dir=(1, 0, 0))


def _latch_arm(side: int) -> Part:
    """The door's latch arm on the left (-1) or right (+1), in the tower frame.

    It prints upright with the column: the root's underside and the barb's are chamfered
    at 45 degrees, so neither overhangs.
    """
    wall = COLUMN_OUTBOARD + COLUMN_WALL  # inside face of the outboard wall
    (y0, y1), (r0, r1) = LATCH_Y, LATCH_ROOT_Z
    zb, top = LATCH_BARB_Z, LATCH_TOP_Z
    tip = COLUMN_OUTBOARD - DOOR_T - LATCH_BARB_OUT
    face = COLUMN_OUTBOARD - DOOR_T - DOOR_CLEARANCE  # the barb's hook holds the door here
    x = LATCH_X

    root = _yz_prism([(wall - 0.1, r0 - (y1 - wall)), (y1, r0), (y1, r1), (wall - 0.1, r1)], x)
    arm = box(x, (y0, y1), (r1 - 0.1, top))
    barb = _yz_prism([(y1, zb), (y0, zb), (tip, zb + y0 - tip), (tip, top), (y1, top)], x)
    # The hook, away from the middle, with a ramp the door's slot rides over as it closes.
    hook = Polyline(
        (x[1] - 0.1, tip, 0),
        (x[1], tip, 0),
        (x[1] + LATCH_BARB, face, 0),
        (x[1] - 0.1, face, 0),
        close=True,
    )
    z = (zb + y0 - tip, top)
    hook = Pos(0, 0, z[0]) * extrude(make_face(hook), amount=z[1] - z[0])
    latch = root + arm + barb + hook
    return latch if side > 0 else latch.mirror(Plane.YZ)


def hood() -> Part:
    """The hood: screws onto the column, carries the yaw servo, and takes the lid."""
    floor_top = HOOD_FLOOR_Z + HOOD_FLOOR_T
    body = _hood_plan(0, (HOOD_FLOOR_Z, LID_Z))
    body -= _hood_plan(HOOD_WALL, (floor_top, LID_Z + 1))
    body += snap_arms(LID_Z, HOOD_SNAPS, LID_T)

    # Yaw servo: through a window in the floor, tabs bolted up through bosses into nuts
    # held in pockets on the bosses' tops, flats towards the window.
    c = p.SERVO_FIT_CLEARANCE
    hl, hw = STD_SERVO_BODY_L / 2 + c, STD_SERVO_BODY_W / 2 + c
    along, across = STD_SERVO_TAB_HOLES
    for dy in (-along / 2, along / 2):
        for x in (-across / 2, across / 2):
            at = (x, YAW_SERVO_BODY_Y + dy)
            body += cylinder(TAB_BOSS_D / 2, (floor_top - 0.1, floor_top + TAB_BOSS_H), at=at)
            screw_z = (HOOD_FLOOR_Z - 1, floor_top + TAB_BOSS_H + 1)
            body -= cylinder(p.STRUCTURAL_SCREW.clearance_d / 2, screw_z, at=at)
            body -= nut_pocket(p.STRUCTURAL_SCREW, floor_top + TAB_BOSS_H, -1, at, angle=30.0)
    floor_z = (HOOD_FLOOR_Z - 1, floor_top + 1)
    body -= box((-hw, hw), (YAW_SERVO_BODY_Y - hl, YAW_SERVO_BODY_Y + hl), floor_z)
    # A notch at the shaft end for the servo's lead, so it pushes straight up. Only as wide as
    # the lead, since it runs between the tab screws: it opens the inside corner of their nut
    # pockets, but the other faces still stop the nuts turning.
    lw = STD_SERVO_LEAD_W / 2 + p.FIT_CLEARANCE
    lead_y = (YAW_SERVO_BODY_Y + hl - 1, YAW_SERVO_BODY_Y + hl + STD_SERVO_LEAD_REACH + c)
    body -= box((-lw, lw), lead_y, (HOOD_FLOOR_Z - 1, floor_top + TAB_BOSS_H + 1))

    # Wire openings: the arm's leads come up through the cable hole, and everything drops
    # into the column through the pass.
    body -= box(*ARM_CABLE_HOLE, floor_z)
    body -= box(*COLUMN_PASS, floor_z)
    for x, y in HOOD_SCREWS:
        body -= cylinder(p.STRUCTURAL_SCREW.clearance_d / 2, floor_z, at=(x, y))
    return body


def hood_lid() -> Part:
    """The hood's lid: snaps on, and lifts off for routing wires in the hood and column."""
    lid = _hood_plan(0, (LID_Z, HOOD_TOP_Z))
    lid = fillet(
        lid.edges().filter_by_position(Axis.Z, HOOD_TOP_Z - 0.1, HOOD_TOP_Z + 0.1), LID_EDGE_R
    )
    return lid - snap_slots(HOOD_SNAPS, LID_T, LID_Z)


def tower_door() -> Part:
    """The access door over the servo driver."""
    (ox0, ox1), (oz0, oz1) = DOOR_OPENING
    o = DOOR_OVERLAP
    c = DOOR_CLEARANCE
    y = (COLUMN_OUTBOARD - DOOR_T, COLUMN_OUTBOARD)
    door = box((ox0 - o, ox1 + o), y, (oz0 - o, oz1 + o))

    # Top hooks: through the opening, then up behind the wall above it. The door hangs on them.
    wall = COLUMN_OUTBOARD + COLUMN_WALL  # inside face of the outboard wall
    foot = wall + c + DOOR_HOOK_TAPER
    back = wall + DOOR_HOOK_LEG_T
    top = oz1 + DOOR_HOOK_LEG_H
    leg = [(wall + c, top), (back, top), (back, oz1 - 4.0), (foot, oz1 - 4.0), (foot, oz1)]
    for sx in (-1, 1):
        hx = sorted((sx * DOOR_HOOK_X[0], sx * DOOR_HOOK_X[1]))
        door += box(hx, (y[1] - 0.1, foot + 0.1), (oz1 - 4.0, oz1 - c))
        door += _yz_prism(leg, hx)

    # Slots for the latch arms' barbs, with room for each arm to flex towards the middle.
    z = (LATCH_BARB_Z + LATCH_Y[0] - COLUMN_OUTBOARD - 0.5, LATCH_TOP_Z + 0.5)
    for sx in (-1, 1):
        sx_span = sorted((sx * (LATCH_X[0] - LATCH_FLEX - c), sx * (LATCH_X[1] + c)))
        door -= box(sx_span, (y[0] - 1, y[1] + 1), z)
    return door
