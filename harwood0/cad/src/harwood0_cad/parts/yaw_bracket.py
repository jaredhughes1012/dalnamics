"""Yaw bracket: hangs from the yaw servo's horn and holds the shoulder servo.

The disc horn seats in the pocket on top and screws on through the holes from
below (screws supplied with the horn); then fit the bracket and horn onto the yaw
servo's spline and drive the horn's centre screw through the centre hole, since the
shoulder servo blocks it afterwards. The DS3218 then drops into the window bottom
first, from the shaft side, its lead through the notch at the window's top end, and
bolts to the plate by its tabs: 4 screws in from behind the plate, nuts on top of the
tabs. Reach the top two through the gap above the servo, from the bracket's open back.

Local frame: origin on the yaw axis at the bracket's top face, with the shoulder
servo's shaft pointing +X. (On the robot the bracket is turned half a turn, so the
shoulder sits on the inboard side.) Print upside down, top face on the bed.
"""

import math

from build123d import Part

from harwood0_cad import params as p
from harwood0_cad.arm_geometry import (
    SHOULDER_DROP,
    SHOULDER_FACE_X,
    STD_HORN_CENTRE_HOLE_D,
    STD_HORN_POCKET,
)
from harwood0_cad.hardware.motors import (
    STD_HORN_D,
    STD_HORN_SCREW_R,
    STD_SERVO_BODY_H,
    STD_SERVO_BODY_L,
    STD_SERVO_BODY_W,
    STD_SERVO_LEAD_REACH,
    STD_SERVO_LEAD_W,
    STD_SERVO_SHAFT_OFFSET,
    STD_SERVO_TAB_HOLES,
    STD_SERVO_TAB_SPAN,
    STD_SERVO_TAB_T,
    STD_SERVO_TAB_TOP,
)
from harwood0_cad.shapes import box, cylinder

TOP_T = 4.0
PLATE_T = 3.0
SIDE_T = 2.0
HALF_W = STD_SERVO_BODY_W / 2 + 4.0
FACE_X = -SHOULDER_FACE_X  # shoulder servo top face, in this part's frame
TAB_FACE_X = FACE_X + STD_SERVO_TAB_TOP - STD_SERVO_TAB_T  # the tabs press on this face
BODY_Z = -SHOULDER_DROP - STD_SERVO_SHAFT_OFFSET  # shoulder servo body centre
BACK_X = FACE_X - STD_SERVO_BODY_H - 2.0  # the bracket's open back

# The top covers the horn's pocket, and the horn screws' heads, under the top, clear the plate.
assert TAB_FACE_X - (STD_HORN_D / 2 + p.FIT_CLEARANCE) >= 2.0, "top does not cover the yaw horn"
assert TAB_FACE_X - PLATE_T - STD_HORN_SCREW_R - p.M3.head_d / 2 >= 1.0, (
    "tab plate blocks the yaw horn's screws"
)


def yaw_bracket() -> Part:
    bottom = BODY_Z - STD_SERVO_TAB_SPAN / 2 - 3.0
    bracket = box((BACK_X, TAB_FACE_X), (-HALF_W, HALF_W), (-TOP_T, 0))
    bracket -= cylinder(STD_HORN_D / 2 + p.FIT_CLEARANCE, (-STD_HORN_POCKET, 0.1))
    bracket -= cylinder(STD_HORN_CENTRE_HOLE_D / 2, (-TOP_T - 1, 1))
    for i in range(4):
        angle = math.radians(45 + 90 * i)
        at = (STD_HORN_SCREW_R * math.cos(angle), STD_HORN_SCREW_R * math.sin(angle))
        bracket -= cylinder(p.M3.clearance_d / 2, (-TOP_T - 1, 1), at=at)

    plate_x = (TAB_FACE_X - PLATE_T, TAB_FACE_X)
    plate = box(plate_x, (-HALF_W, HALF_W), (bottom, -TOP_T + 0.1))
    c = p.SERVO_FIT_CLEARANCE
    hl, hw = STD_SERVO_BODY_L / 2 + c, STD_SERVO_BODY_W / 2 + c
    plate -= box((plate_x[0] - 1, plate_x[1] + 1), (-hw, hw), (BODY_Z - hl, BODY_Z + hl))
    # A notch at the top (shaft) end for the servo's lead, so it slides straight in. Only as
    # wide as the lead, since it runs between the tab screws.
    lw = STD_SERVO_LEAD_W / 2 + p.FIT_CLEARANCE
    lead_z = (BODY_Z + hl - 1, BODY_Z + hl + STD_SERVO_LEAD_REACH + c)
    plate -= box((plate_x[0] - 1, plate_x[1] + 1), (-lw, lw), lead_z)
    along, across = STD_SERVO_TAB_HOLES
    for dz in (-along / 2, along / 2):
        for y in (-across / 2, across / 2):
            plate -= cylinder(
                p.STRUCTURAL_SCREW.clearance_d / 2,
                (plate_x[0] - 1, plate_x[1] + 1),
                axis="x",
                at=(y, BODY_Z + dz),
            )
    bracket += plate

    for side in (-1, 1):
        y = sorted((side * HALF_W, side * (HALF_W - SIDE_T)))
        bracket += box((BACK_X, plate_x[0] + 0.1), y, (BODY_Z, -TOP_T + 0.1))
    return bracket
