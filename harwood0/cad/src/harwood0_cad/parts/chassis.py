"""Chassis: the rover's body, holding the drive motors, battery, electronics, and front camera.

A flat open-topped box with a rounded nose. Two lengthwise inner walls carry the
four motors, each bolted through by its gearbox face (2x M3), with the shaft
passing out into an arched wheel well in the body side. Between each pair of
wells is a side bay: the UBEC sits in the left one, the ULN2003 in the right one.
The battery, Uno, and TB6612s sit in the centre bay. Only the Uno and ULN2003
screw down; the battery, UBEC, and TB6612s are held to the floor with double-sided tape. The ESP32-CAM stands in
grooves behind a window in the nose.

The top plate (which carries the track and frames the work table) snaps onto
the wall tops: snap arms rise from the walls through slots in the plate.
Everything inside is reachable by lifting out the table, or by unsnapping the
top plate.

Local frame: the global XY origin, with Z=0 at the floor underside.
Printed as modelled, floor down. The well arches print as bridges.
"""

from build123d import Axis, Part, fillet

from harwood0_cad import params as p
from harwood0_cad.hardware.boards import (
    ESP32_CAM_HEADER_LEN,
    ESP32_CAM_L,
    ESP32_CAM_LENS_Y,
    ESP32_CAM_W,
    PCB_T,
    ULN2003_HOLE_INSET,
    ULN2003_L,
    ULN2003_W,
    UNO_HOLES,
)
from harwood0_cad.hardware.motors import (
    GA25_BOSS_D,
    GA25_CAN_D,
    GA25_FACE_HOLE_SPACING,
    GA25_GEARBOX_L,
)
from harwood0_cad.parts.body import body_plan
from harwood0_cad.parts.snaps import snap_arms
from harwood0_cad.shapes import box, cylinder

T = p.BODY_WALL_T
H = p.SUPPORT_Z - p.FLOOR_Z  # wall tops, where the top plate sits
AXLE_H = p.AXLE_Z - p.FLOOR_Z
FLOOR = p.FLOOR_T

SADDLE_Y = p.MOTOR_FACE_Y - GA25_GEARBOX_L - 12  # under each motor can
WIRE_HOLE_D = 14.0
WIRE_HOLE_Z = H - 12.0  # through the motor walls, above the battery and boards

CAMERA_WINDOW = 20.0  # square, centred on the lens's nominal position
CAMERA_WINDOW_R = 3.0
CAMERA_LIP_T = 1.2
CAMERA_LIP_OVERLAP = 1.5
CAMERA_RAIL_T = 2.0


def _interior(z_top: float = H) -> Part:
    return body_plan(T - 0.5, (FLOOR - 0.1, z_top))


def _wells() -> Part:
    wells = None
    for x in (-p.MOTOR_X, p.MOTOR_X):
        for side in (-1, 1):
            y = sorted((side * p.MOTOR_WALL_Y, side * (p.CHASSIS_W / 2 + 1)))
            well = box((x - p.WELL_R, x + p.WELL_R), y, (-1, AXLE_H))
            well += cylinder(p.WELL_R, y, axis="y", at=(x, AXLE_H))
            wells = well if wells is None else wells + well
    return wells


def _walls() -> Part:
    """Motor walls and the well dividers, trimmed to the interior."""
    walls = None
    for side in (-1, 1):
        y = sorted((side * p.MOTOR_FACE_Y, side * p.MOTOR_WALL_Y))
        wall = box((-p.CHASSIS_L / 2, p.CHASSIS_L / 2), y, (FLOOR - 0.1, H))
        for x in (-p.WELL_DIVIDER_X, p.WELL_DIVIDER_X):
            xs = sorted((x, x - (1 if x > 0 else -1) * p.WELL_DIVIDER_T))
            wall += box(
                xs,
                sorted((side * p.MOTOR_WALL_Y, side * p.CHASSIS_W / 2)),
                (FLOOR - 0.1, H),
            )
        walls = wall if walls is None else walls + wall
    return walls & _interior(H)


def _motor_mounts(shell: Part) -> Part:
    for x in (-p.MOTOR_X, p.MOTOR_X):
        for side in (-1, 1):
            wall = sorted((side * (p.MOTOR_FACE_Y - 1), side * (p.MOTOR_WALL_Y + 1)))
            shell -= cylinder((GA25_BOSS_D + 1) / 2, wall, axis="y", at=(x, AXLE_H))
            for dx in (-GA25_FACE_HOLE_SPACING / 2, GA25_FACE_HOLE_SPACING / 2):
                shell -= cylinder(p.M3_CLEARANCE_D / 2, wall, axis="y", at=(x + dx, AXLE_H))

            sy = side * SADDLE_Y
            saddle = box((x - 10, x + 10), (sy - 2, sy + 2), (FLOOR - 0.1, AXLE_H))
            r = GA25_CAN_D / 2 + p.FIT_CLEARANCE
            shell += saddle - cylinder(r, (sy - 3, sy + 3), axis="y", at=(x, AXLE_H))
    return shell


def _board_standoffs() -> Part:
    """Standoffs for the two screwed-down boards. The battery, UBEC, and TB6612s are taped
    to the floor."""
    ux, uy = p.UNO_ORIGIN
    standoffs = [(ux - hx, uy - hy) for hx, hy in UNO_HOLES]  # board is rotated 180 deg
    cx, cy = p.ULN2003_CENTER
    ix, iy = ULN2003_L / 2 - ULN2003_HOLE_INSET, ULN2003_W / 2 - ULN2003_HOLE_INSET
    standoffs += [(cx + sx * ix, cy + sy * iy) for sx in (-1, 1) for sy in (-1, 1)]
    top = FLOOR + p.UNO_STANDOFF_H
    mounts = None
    for x, y in standoffs:
        standoff = cylinder(p.BOARD_STANDOFF_D / 2, (FLOOR - 0.1, top), at=(x, y))
        mounts = standoff if mounts is None else mounts + standoff
        mounts -= cylinder(p.M3_PILOT_D / 2, (FLOOR, top + 1), at=(x, y))
    return mounts


def _camera_mount() -> Part:
    """Two grooved posts the ESP32-CAM slides down into, camera end up, facing forward."""
    front = p.CAMERA_PCB_FRONT_X
    back = front - PCB_T
    x = (back - 0.1 - 2.5, front + 0.1 + CAMERA_LIP_T)
    edge = ESP32_CAM_W / 2 + 0.2
    top = FLOOR + ESP32_CAM_L - 6
    header_top = FLOOR + ESP32_CAM_HEADER_LEN + 0.5
    posts = None
    for side in (-1, 1):
        rail = box(x, sorted((side * edge, side * (edge + CAMERA_RAIL_T))), (FLOOR - 0.1, top))
        lip_y = sorted((side * edge, side * (edge - CAMERA_LIP_OVERLAP)))
        rail += box((front + 0.1, x[1]), lip_y, (FLOOR - 0.1, top))
        # The back lip stops above the header pins, which run along the bottom half.
        rail += box((x[0], back - 0.1), lip_y, (header_top, top))
        posts = rail if posts is None else posts + rail
    return posts


def chassis() -> Part:
    shell = body_plan(0, (0, H))
    shell = fillet(shell.edges().filter_by_position(Axis.Z, -0.01, 0.01), p.BOTTOM_EDGE_R)
    shell -= body_plan(T, (FLOOR, H + 1))
    shell += _walls()
    shell -= _wells()
    shell = _motor_mounts(shell)

    shell += snap_arms(H)

    shell += _board_standoffs()
    shell += _camera_mount()

    # A window for the lens, oversized because the lens hangs on a flex cable and its
    # position on the board varies from module to module.
    lens_z = FLOOR + ESP32_CAM_L / 2 + ESP32_CAM_LENS_Y
    h = CAMERA_WINDOW / 2
    window = box((p.CHASSIS_L / 2 - T - 1, p.CHASSIS_L / 2 + 1), (-h, h), (lens_z - h, lens_z + h))
    shell -= fillet(window.edges().filter_by(Axis.X), CAMERA_WINDOW_R)

    for side in (-1, 1):
        wall = sorted((side * (p.MOTOR_FACE_Y - 1), side * (p.MOTOR_WALL_Y + 1)))
        shell -= cylinder(WIRE_HOLE_D / 2, wall, axis="y", at=(0, WIRE_HOLE_Z))
    return shell


# The front-left corner, for a test print: the nose camera grooves and window, one motor
# mount and wheel well (from the well divider to the outside), and a top plate snap arm.
FIT_SECTION_X = (p.WELL_DIVIDER_X - p.WELL_DIVIDER_T - 3.0, p.CHASSIS_L / 2 + 1)
FIT_SECTION_Y = (-20.0, p.CHASSIS_W / 2 + 1)


def chassis_fit_section() -> Part:
    """A corner of the chassis to test fits before printing the whole body."""
    return chassis() & box(FIT_SECTION_X, FIT_SECTION_Y, (-1, H + 20))
