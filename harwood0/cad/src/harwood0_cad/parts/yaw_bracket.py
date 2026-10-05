"""Yaw bracket: hangs from the yaw servo's horn and holds the shoulder servo.

The disc horn seats in the pocket on top and screws on through the four holes
(screws supplied with the horn); fit the horn's centre screw first, since the
shoulder servo blocks it afterwards. The DS3218 then slides in through the
window, shaft first, and screws to the plate by its tabs (4x M3).

Local frame: origin on the yaw axis at the bracket's top face, with the shoulder
servo's shaft pointing +X. (On the robot the bracket is turned half a turn, so the
shoulder sits on the inboard side.) Print upside down, top face on the bed.
"""

import math

from build123d import Part

from harwood0_cad import params as p
from harwood0_cad.arm_geometry import SHOULDER_DROP, STD_HORN_POCKET
from harwood0_cad.hardware.motors import (
    STD_HORN_D,
    STD_HORN_SCREW_R,
    STD_SERVO_BODY_H,
    STD_SERVO_BODY_L,
    STD_SERVO_BODY_W,
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
FACE_X = 15.0  # shoulder servo top face, in this part's frame
TAB_FACE_X = FACE_X + STD_SERVO_TAB_TOP - STD_SERVO_TAB_T  # the tabs press on this face
BODY_Z = -SHOULDER_DROP - STD_SERVO_SHAFT_OFFSET  # shoulder servo body centre
SERVO_SCREW_PILOT_D = p.M3_PILOT_D


def yaw_bracket() -> Part:
    back_x = FACE_X - STD_SERVO_BODY_H - 2.0
    bottom = BODY_Z - STD_SERVO_TAB_SPAN / 2 - 3.0
    bracket = box((back_x, TAB_FACE_X), (-HALF_W, HALF_W), (-TOP_T, 0))
    bracket -= cylinder(STD_HORN_D / 2 + p.FIT_CLEARANCE, (-STD_HORN_POCKET, 0.1))
    bracket -= cylinder(2.0, (-TOP_T - 1, 1))
    for i in range(4):
        angle = math.radians(45 + 90 * i)
        at = (STD_HORN_SCREW_R * math.cos(angle), STD_HORN_SCREW_R * math.sin(angle))
        bracket -= cylinder(p.M3_CLEARANCE_D / 2 - 0.2, (-TOP_T - 1, 1), at=at)

    plate_x = (TAB_FACE_X - PLATE_T, TAB_FACE_X)
    plate = box(plate_x, (-HALF_W, HALF_W), (bottom, -TOP_T + 0.1))
    c = p.FIT_CLEARANCE
    hl, hw = STD_SERVO_BODY_L / 2 + c, STD_SERVO_BODY_W / 2 + c
    plate -= box((plate_x[0] - 1, plate_x[1] + 1), (-hw, hw), (BODY_Z - hl, BODY_Z + hl))
    along, across = STD_SERVO_TAB_HOLES
    for dz in (-along / 2, along / 2):
        for y in (-across / 2, across / 2):
            plate -= cylinder(
                SERVO_SCREW_PILOT_D / 2,
                (plate_x[0] - 1, plate_x[1] + 1),
                axis="x",
                at=(y, BODY_Z + dz),
            )
    bracket += plate

    for side in (-1, 1):
        y = sorted((side * HALF_W, side * (HALF_W - SIDE_T)))
        bracket += box((back_x, plate_x[0] + 0.1), y, (BODY_Z, -TOP_T + 0.1))
    return bracket
