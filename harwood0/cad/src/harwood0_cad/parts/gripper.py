"""Parallel gripper: base, gear, and the two jaws.

The gripper servo is screwed into the forearm first. The base then screws onto the
forearm over it (2 screws from the forearm's back face,
into inserts in its legs), with the servo's spline
coming up through the centre. The gear takes the servo horn, with its arms trimmed
to GRIPPER_HORN_L, in a pocket on its back face and is held by the horn screw. Each jaw is a rack whose dovetail
tongue slides into a groove in the base from the side; the front jaw meshes on
the gear's far side and the rear jaw on its near side, so turning the gear opens
or closes both fingers together, keeping them parallel.

The arm camera (an ESP32-CAM) slides into a cradle on the back of the base, lens
facing the fingertips from just outside the jaws, and rests on two stops at its
SD-card end. Its header pins point back up the forearm for the wiring.

All four parts share the forearm frame (origin on the elbow axis at the forearm's
back face, the forearm along +Y, the gripper axis along X at y=GRIPPER_Y). Each
prints flat on its back face.
"""

import math

from build123d import Part, Polyline, extrude, make_face

from harwood0_cad import params as p
from harwood0_cad.arm_geometry import (
    FINGER_CURVE,
    FINGER_GAP,
    FINGER_REACH,
    FINGER_T,
    FINGER_TIP_W,
    FINGER_W,
    FOREARM_T,
    GRIPPER_BASE_X,
    GRIPPER_GEAR_MODULE,
    GRIPPER_GEAR_R,
    GRIPPER_GEAR_T,
    GRIPPER_GEAR_TEETH,
    GRIPPER_GEAR_X,
    GRIPPER_HORN_L,
    GRIPPER_Y,
    JAW_TONGUE_Y,
    MG90S_HORN_POCKET,
    RACK_BODY_T,
    RACK_LENGTH,
    RACK_ROOT,
)
from harwood0_cad.gears import PRESSURE_ANGLE, gear_profile, rack_teeth
from harwood0_cad.hardware.boards import ESP32_CAM_HEADER_LEN, ESP32_CAM_L, ESP32_CAM_W, PCB_T
from harwood0_cad.hardware.motors import (
    MG90S_BODY_W,
    MG90S_GEAR_BOSS_D,
    MG90S_HORN_ARM_W,
    MG90S_HORN_HUB_D,
)
from harwood0_cad.parts.fasteners import insert_hole
from harwood0_cad.shapes import box, cylinder

TONGUE_W = (3.5, 5.5)  # dovetail width at the base's top face, and at the groove bottom
TONGUE_DEPTH = 2.5
TONGUE_CLEARANCE = 0.25
BASE_HALF_Z = 12.0
FINGER_POINTS = 12
BASE_HALF_Y = RACK_ROOT + RACK_BODY_T + 1.5
LEG_Z = (MG90S_BODY_W / 2 + 0.6, MG90S_BODY_W / 2 + 3.2)  # legs either side of the servo body
# Two screws from the forearm's back face, one into an insert in each leg at opposite ends.
# The legs are too thin for an insert, so each gets a boss, kept clear of the servo body.
BASE_SCREW_Z = LEG_Z[0] + p.STRUCTURAL_SCREW.insert_boss_d / 2
BASE_SCREWS = (
    (GRIPPER_Y - BASE_HALF_Y + 4, BASE_SCREW_Z),
    (GRIPPER_Y + BASE_HALF_Y - 4, -BASE_SCREW_Z),
)

# Arm camera: its PCB stands across the back of the base with its long axis along X, the
# camera end outermost so the lens looks along the jaws from just outside the fingers' plane.
CAM_CENTER_X = 26.0
CAM_FRONT_Y = GRIPPER_Y - BASE_HALF_Y - 2.5  # PCB front (lens) face
CAM_RAIL_T = 2.0
CAM_LIP_T = 1.2
CAM_LIP_OVERLAP = 1.5
CAM_BACK_T = 2.5


def _dovetail(y: float, z: tuple[float, float], top_x: float, grow: float = 0.0) -> Part:
    """A dovetail along Z, narrow at `top_x` and widening towards -X, centred on `y`."""
    narrow, wide = TONGUE_W[0] / 2 + grow, TONGUE_W[1] / 2 + grow
    bottom = top_x - TONGUE_DEPTH - grow
    profile = Polyline(
        (top_x + 0.01, y - narrow, z[0]),
        (top_x + 0.01, y + narrow, z[0]),
        (bottom, y + wide, z[0]),
        (bottom, y - wide, z[0]),
        close=True,
    )
    return extrude(make_face(profile), amount=z[1] - z[0], dir=(0, 0, 1))


def gripper_base() -> Part:
    y0, y1 = GRIPPER_Y - BASE_HALF_Y, GRIPPER_Y + BASE_HALF_Y
    floor = box(GRIPPER_BASE_X, (y0, y1), (-BASE_HALF_Z, BASE_HALF_Z))
    for side in (-1, 1):
        groove_y = GRIPPER_Y + side * JAW_TONGUE_Y
        floor -= _dovetail(
            groove_y, (-BASE_HALF_Z - 1, BASE_HALF_Z + 1), GRIPPER_BASE_X[1], TONGUE_CLEARANCE
        )
    floor -= cylinder(
        MG90S_GEAR_BOSS_D / 2 + 0.6,
        (GRIPPER_BASE_X[0] - 1, GRIPPER_BASE_X[1] + 1),
        axis="x",
        at=(GRIPPER_Y, 0),
    )
    for side in (-1, 1):
        z = sorted((side * LEG_Z[0], side * LEG_Z[1]))
        floor += box((FOREARM_T, GRIPPER_BASE_X[0] + 0.1), (y0, y1), z)
    for y, z in BASE_SCREWS:
        boss_x = (FOREARM_T, GRIPPER_BASE_X[0] + 0.1)
        floor += cylinder(p.STRUCTURAL_SCREW.insert_boss_d / 2, boss_x, axis="x", at=(y, z))
        floor -= insert_hole(p.STRUCTURAL_SCREW, FOREARM_T, 1, (y, z), axis="x")
    return floor + _camera_cradle()


def _camera_cradle() -> Part:
    """Rails along the camera's long edges, lips front and back, and stops at its inner end."""
    front, back = CAM_FRONT_Y, CAM_FRONT_Y - PCB_T
    half_w = ESP32_CAM_W / 2 + 0.2
    x0 = CAM_CENTER_X - ESP32_CAM_L / 2  # the board's SD-card end, against the stops
    x1 = CAM_CENTER_X + ESP32_CAM_L / 2
    header_end = x0 + ESP32_CAM_HEADER_LEN + 0.5
    y = (back - 0.15 - CAM_BACK_T, front + 0.15 + CAM_LIP_T)
    cradle = None
    for side in (-1, 1):
        rail_z = sorted((side * half_w, side * (half_w + CAM_RAIL_T)))
        lip_z = sorted((side * half_w, side * (half_w - CAM_LIP_OVERLAP)))
        part = box((x0 - 2, x1), y, rail_z)
        part += box((x0, x1), (front + 0.15, y[1]), lip_z)
        part += box((header_end, x1), (y[0], back - 0.15), lip_z)  # behind the camera half only
        part += box((x0 - 2, x0), y, lip_z)  # stop
        # Tie the rails to the base.
        part += box(
            GRIPPER_BASE_X,
            (front + 0.15, GRIPPER_Y - BASE_HALF_Y + 0.1),
            sorted((side * (BASE_HALF_Z - 1), side * (half_w + CAM_RAIL_T))),
        )
        cradle = part if cradle is None else cradle + part
    return cradle


def gripper_gear() -> Part:
    outline = gear_profile(GRIPPER_GEAR_TEETH, GRIPPER_GEAR_MODULE, PRESSURE_ANGLE)
    face = make_face(
        Polyline(*[(GRIPPER_GEAR_X, GRIPPER_Y + y, z) for y, z in outline], close=True)
    )
    gear = extrude(face, amount=GRIPPER_GEAR_T, dir=(1, 0, 0))
    z = (GRIPPER_GEAR_X - 0.1, GRIPPER_GEAR_X + MG90S_HORN_POCKET)
    w = MG90S_HORN_ARM_W + 2 * p.FIT_CLEARANCE
    half = GRIPPER_HORN_L / 2 + p.FIT_CLEARANCE - w / 2
    pocket = box(z, (GRIPPER_Y - half, GRIPPER_Y + half), (-w / 2, w / 2))
    for y in (GRIPPER_Y - half, GRIPPER_Y + half):
        pocket += cylinder(w / 2, z, axis="x", at=(y, 0))
    pocket += cylinder(MG90S_HORN_HUB_D / 2 + 0.5, z, axis="x", at=(GRIPPER_Y, 0))
    gear -= pocket
    return gear - cylinder(
        1.25, (GRIPPER_GEAR_X - 1, GRIPPER_GEAR_X + GRIPPER_GEAR_T + 1), axis="x", at=(GRIPPER_Y, 0)
    )


def _finger(side: int, root_y: float, x: tuple[float, float]) -> Part:
    """A finger from `root_y` to the fingertips, on the +Z (side=1) or -Z (side=-1) side.

    Straight up to the front rack, then bowing outward and back in so the tips meet,
    tapering as it goes.
    """
    curve_start = GRIPPER_Y + RACK_ROOT + RACK_BODY_T
    tip_y = p.FOREARM_L
    inner, outer = [(root_y, FINGER_GAP)], [(root_y, FINGER_GAP + FINGER_W)]
    for i in range(FINGER_POINTS + 1):
        t = i / FINGER_POINTS
        y = curve_start + t * (tip_y - curve_start)
        z_in = FINGER_GAP + FINGER_CURVE * math.sin(math.pi * t)
        inner.append((y, z_in))
        outer.append((y, z_in + FINGER_W + t * (FINGER_TIP_W - FINGER_W)))
    outline = inner + list(reversed(outer))
    face = make_face(Polyline(*[(x[0], y, side * z) for y, z in outline], close=True))
    return extrude(face, amount=x[1] - x[0], dir=(1, 0, 0))


def _jaw(side: int) -> Part:
    """A jaw closed, its rack on the given side of the gear (+1 front, -1 rear)."""
    rack_y = sorted((GRIPPER_Y + side * RACK_ROOT, GRIPPER_Y + side * (RACK_ROOT + RACK_BODY_T)))
    gear_x = (GRIPPER_GEAR_X, GRIPPER_GEAR_X + GRIPPER_GEAR_T)
    half = RACK_LENGTH / 2
    jaw = box(gear_x, rack_y, (-half, half))
    # Start the teeth on a whole pitch so a gap sits at z=0, where a gear tooth points when
    # closed; the jaw and gear then stay in mesh as the gear turns.
    pitch = math.pi * GRIPPER_GEAR_MODULE
    first = -pitch * math.floor(half / pitch)
    jaw += rack_teeth(
        GRIPPER_GEAR_MODULE,
        start=(gear_x[0], GRIPPER_Y + side * RACK_ROOT, first),
        length=-2 * first,
        width=GRIPPER_GEAR_T,
        facing=-side,
    )
    jaw += _dovetail(GRIPPER_Y + side * JAW_TONGUE_Y, (-half, half), gear_x[0])

    # The finger: front jaw on the +Z side of the centreline, rear jaw on the -Z side.
    finger_side = 1 if side > 0 else -1
    finger_z = sorted((finger_side * FINGER_GAP, finger_side * (FINGER_GAP + FINGER_W)))
    finger_x = (gear_x[1] + 0.5, gear_x[1] + 0.5 + FINGER_T)
    jaw += box((gear_x[0], finger_x[1]), rack_y, finger_z)
    return jaw + _finger(finger_side, min(rack_y), finger_x)


def gripper_jaw_front() -> Part:
    return _jaw(1)


def gripper_jaw_rear() -> Part:
    return _jaw(-1)


assert abs(GRIPPER_Y + RACK_ROOT + RACK_BODY_T + FINGER_REACH - p.FOREARM_L) < 1e-6
assert GRIPPER_GEAR_R - 1.25 * GRIPPER_GEAR_MODULE > GRIPPER_HORN_L / 2 + 0.5, (
    "trimmed horn does not fit the gear"
)
