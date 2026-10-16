"""Arm links: the upper arm and the forearm (which carries the gripper).

Each joint is an MG90S or a DS3218 whose horn seats in a pocket on the next link's
back face and is held by the servo's centre horn screw (disc horns also take four
screws). Each MG90S slides through a window in the link that carries it, shaft
first, and screws on by its tabs using the screws supplied with the servo.

Printed C-clips along each link's edge carry the elbow, gripper, and arm camera
leads up to the shoulder; press each flat lead in through the gap in the clip's
outer wall.

Frames: each part's origin is on its joint axis at its back (servo-side) face,
with the joint axis along X and the link running along +Y at zero angle. Both
print flat on their back faces with no supports.
"""

import math

from build123d import Part

from harwood0_cad import params as p
from harwood0_cad.arm_geometry import (
    FOREARM_T,
    GRIPPER_Y,
    LINK_T,
    MG90S_HORN_POCKET,
    STD_HORN_POCKET,
)
from harwood0_cad.hardware.motors import (
    MG90S_BODY_L,
    MG90S_BODY_W,
    MG90S_HORN_ARM_W,
    MG90S_HORN_HUB_D,
    MG90S_HORN_LENGTH,
    MG90S_SHAFT_OFFSET,
    MG90S_TAB_HOLE_SPACING,
    STD_HORN_D,
    STD_HORN_SCREW_R,
)
from harwood0_cad.shapes import Span, box, cylinder

LINK_W = 18.0
SHOULDER_DISC_R = 16.0
SERVO_SCREW_PILOT_D = 1.6
WIRE_CLIP_HOLE = (8.0, 3.0)  # a servo plug passes through
WIRE_CLIP_GAP = 1.6  # opening in the clip's outer wall, for pressing leads in sideways
UPPER_ARM_CLIPS = (35.0, 70.0)
FOREARM_CLIPS = (18.0, 34.0)  # clear of the arm camera's header pins
HORN_SCREW_D = 2.5


def _bar(x: Span, y: Span, half_w: float) -> Part:
    """A flat bar along Y with rounded ends."""
    bar = box(x, y, (-half_w, half_w))
    for end in y:
        bar += cylinder(half_w, x, axis="x", at=(end, 0))
    return bar


def _wire_clip(y: float, side: int) -> Part:
    """A C-shaped clip on the link's edge (`side` +1 for +Z, -1 for -Z) that wire runs through along Y."""
    edge = side * LINK_W / 2
    z = sorted((edge - side * 0.5, edge + side * (WIRE_CLIP_HOLE[1] + 3.0)))
    hole_z = sorted((edge + side * 1.5, edge + side * (1.5 + WIRE_CLIP_HOLE[1])))
    clip = box((0, WIRE_CLIP_HOLE[0] + 3.0), (y - 3, y + 3), z)
    clip -= box((1.5, 1.5 + WIRE_CLIP_HOLE[0]), (y - 4, y + 4), hole_z)
    # A gap in the outer wall, so a flat servo lead presses in sideways.
    mid = sum(hole_z) / 2
    gap = (1.5 + WIRE_CLIP_HOLE[0] - 0.1, WIRE_CLIP_HOLE[0] + 4.0)
    return clip - box(gap, (y - 4, y + 4), (mid - WIRE_CLIP_GAP / 2, mid + WIRE_CLIP_GAP / 2))


def _mg90s_horn_pocket(at_y: float) -> Part:
    """Pocket in a back face for an MG90S double horn, arms along Y."""
    z = (-0.1, MG90S_HORN_POCKET)
    w = MG90S_HORN_ARM_W + 2 * p.FIT_CLEARANCE
    half = MG90S_HORN_LENGTH / 2 + p.FIT_CLEARANCE - w / 2
    pocket = box(z, (at_y - half, at_y + half), (-w / 2, w / 2))
    for y in (at_y - half, at_y + half):
        pocket += cylinder(w / 2, z, axis="x", at=(y, 0))
    pocket += cylinder(MG90S_HORN_HUB_D / 2 + 0.5, z, axis="x", at=(at_y, 0))
    return pocket + cylinder(HORN_SCREW_D / 2, (-1, 20), axis="x", at=(at_y, 0))


def _mg90s_mount(link_t: float, shaft_y: float) -> Part:
    """Window and tab pilot holes for an MG90S whose shaft sits at `shaft_y`, pointing +X."""
    c = p.FIT_CLEARANCE
    body_y = shaft_y - MG90S_SHAFT_OFFSET
    hl, hw = MG90S_BODY_L / 2 + c, MG90S_BODY_W / 2 + c
    cut = box((-1, link_t + 1), (body_y - hl, body_y + hl), (-hw, hw))
    for dy in (-MG90S_TAB_HOLE_SPACING / 2, MG90S_TAB_HOLE_SPACING / 2):
        cut += cylinder(SERVO_SCREW_PILOT_D / 2, (-1, link_t + 1), axis="x", at=(body_y + dy, 0))
    return cut


def upper_arm() -> Part:
    length = p.UPPER_ARM_L
    link = _bar((0, LINK_T), (0, length + 14), LINK_W / 2)
    link += cylinder(SHOULDER_DISC_R, (0, LINK_T), axis="x")
    link -= cylinder(STD_HORN_D / 2 + p.FIT_CLEARANCE, (-0.1, STD_HORN_POCKET), axis="x")
    link -= cylinder(2.0, (-1, LINK_T + 1), axis="x")
    for i in range(4):
        angle = math.radians(45 + 90 * i)
        at = (STD_HORN_SCREW_R * math.cos(angle), STD_HORN_SCREW_R * math.sin(angle))
        link -= cylinder(p.M3.clearance_d / 2 - 0.2, (-1, LINK_T + 1), axis="x", at=at)
    link -= _mg90s_mount(LINK_T, length)
    # The upper arm is mounted mirrored, so its -Z edge is the top one.
    for y in UPPER_ARM_CLIPS:
        link += _wire_clip(y, -1)
    return link


def forearm() -> Part:
    # Import here: the gripper module's layout depends on this one's joint stack.
    from harwood0_cad.parts.gripper import BASE_HALF_Y, BASE_SCREW_Z, BASE_SCREWS

    tip_end = GRIPPER_Y + BASE_HALF_Y
    arm = _bar((0, FOREARM_T), (-8, tip_end - LINK_W / 2), LINK_W / 2)
    pad_z = BASE_SCREW_Z + p.STRUCTURAL_SCREW.head_d / 2 + 1.5  # round the base's screw heads
    arm += box((0, FOREARM_T), (GRIPPER_Y - BASE_HALF_Y, tip_end), (-pad_z, pad_z))
    arm += cylinder(MG90S_HORN_LENGTH / 2 + 2, (0, FOREARM_T), axis="x")
    arm -= _mg90s_horn_pocket(0)
    arm -= _mg90s_mount(FOREARM_T, GRIPPER_Y)
    for y, z in BASE_SCREWS:
        arm -= cylinder(
            p.STRUCTURAL_SCREW.clearance_d / 2, (-1, FOREARM_T + 1), axis="x", at=(y, z)
        )
        arm -= cylinder(p.STRUCTURAL_SCREW.head_d / 2 + 0.2, (-1, 1.5), axis="x", at=(y, z))
    for y in FOREARM_CLIPS:
        arm += _wire_clip(y, 1)
    return arm
