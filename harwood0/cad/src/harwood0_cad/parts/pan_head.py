"""Pan head: rides on the pan stepper's shaft and carries the tilt servo.

The disc presses onto the stepper's double-D shaft. The MG90S slides through
the upright holder, shaft first, and is screwed on by its tabs using the two
screws supplied with the servo. Its output shaft points -Y and defines the
tilt axis, which crosses the pan axis.

Local frame: origin on the pan axis at the disc underside; the tilt axis is
along Y at Z=TILT_AXIS_H. Printed as modelled, disc down, with no supports.
"""

from build123d import Part

from harwood0_cad import params as p
from harwood0_cad.hardware.motors import (
    BYJ_BOSS_H,
    BYJ_FLAT_L,
    BYJ_SHAFT_D,
    BYJ_SHAFT_FLAT,
    BYJ_SHAFT_L,
    MG90S_BODY_L,
    MG90S_BODY_W,
    MG90S_SHAFT_OFFSET,
    MG90S_TAB_HOLE_SPACING,
    MG90S_TAB_SPAN,
    MG90S_TAB_T,
    MG90S_TAB_TOP,
)
from harwood0_cad.shapes import box, cylinder, double_d_shaft

DISC_D = 52.0
DISC_T = 4.0
HUB_D = 12.0
SERVO_TOP_Y = 9.0  # servo body top face (the face the shaft leaves), along +Y
HOLDER_T = 3.0
HOLDER_Y = SERVO_TOP_Y - MG90S_TAB_TOP + MG90S_TAB_T  # tab underside rests here
SERVO_SCREW_PILOT_D = 1.6

# Where the stepper shaft lands, relative to the disc underside.
SHAFT_BASE = p.STEPPER_FLANGE_Z + BYJ_BOSS_H - p.PAN_HEAD_Z
SHAFT_TIP = SHAFT_BASE + BYJ_SHAFT_L


def pan_head() -> Part:
    head = cylinder(DISC_D / 2, (0, DISC_T))
    hub_bottom = SHAFT_BASE + 1.0
    head += cylinder(HUB_D / 2, (hub_bottom, SHAFT_TIP + 1.5))
    flat_start = SHAFT_TIP - BYJ_FLAT_L
    head -= cylinder(BYJ_SHAFT_D / 2 + 0.15, (hub_bottom - 1, flat_start))
    bore_flat = BYJ_SHAFT_FLAT + p.FIT_CLEARANCE
    head -= double_d_shaft(BYJ_SHAFT_D + 0.3, bore_flat, (flat_start - 0.01, SHAFT_TIP + 0.5))

    body_x = -MG90S_SHAFT_OFFSET
    z = p.TILT_AXIS_H
    holder_x = (body_x - MG90S_TAB_SPAN / 2 - 3, body_x + MG90S_TAB_SPAN / 2 + 3)
    holder_y = (HOLDER_Y, HOLDER_Y + HOLDER_T)
    holder = box(holder_x, holder_y, (0, z + MG90S_BODY_W / 2 + 5))
    for x in holder_x[0], holder_x[1] - HOLDER_T:
        holder += box((x, x + HOLDER_T), (holder_y[1] - 0.1, holder_y[1] + 10), (0, 20))
    c = p.FIT_CLEARANCE
    window_x = (body_x - MG90S_BODY_L / 2 - c, body_x + MG90S_BODY_L / 2 + c)
    window_z = (z - MG90S_BODY_W / 2 - c, z + MG90S_BODY_W / 2 + c)
    holder -= box(window_x, (holder_y[0] - 1, holder_y[1] + 1), window_z)
    for dx in (-MG90S_TAB_HOLE_SPACING / 2, MG90S_TAB_HOLE_SPACING / 2):
        holder -= cylinder(
            SERVO_SCREW_PILOT_D / 2,
            (holder_y[0] - 1, holder_y[1] + 1),
            axis="y",
            at=(body_x + dx, z),
        )
    return head + holder
