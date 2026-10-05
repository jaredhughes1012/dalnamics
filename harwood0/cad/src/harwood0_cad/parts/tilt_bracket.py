"""Tilt bracket: bolts to the servo horn and holds the ESP32-CAM.

The horn seats in a pocket on the bracket's back face and is clamped by the
servo's own horn screw, driven through the centre hole. The ESP32-CAM slides
down into the cradle's side grooves from the top and rests on the bottom stop.
Its header pins stay reachable at the back. The board sits forward of the tilt
axis so the screwdriver has a clear path to the horn screw.

Local frame: origin on the tilt axis at the bracket's back (servo-side) face;
the tilt axis is Y, the camera looks along +X. Print with the back face (+Y)
down on the bed, with no supports.
"""

from build123d import Part

from harwood0_cad import params as p
from harwood0_cad.hardware.boards import ESP32_CAM_HEADER_LEN, ESP32_CAM_L, ESP32_CAM_W, PCB_T
from harwood0_cad.hardware.motors import MG90S_HORN_ARM_W, MG90S_HORN_HUB_D, MG90S_HORN_LENGTH
from harwood0_cad.shapes import box, cylinder

PLATE_T = 4.5
HORN_POCKET_DEPTH = 1.8
HORN_SCREW_D = 2.5

# Camera placement in this frame.
CAM_PCB_BACK_X = 5.0  # forward of the tilt axis, leaving the horn screw path clear
CAM_EDGE_GAP = 2.0  # side rail thickness
CAM_CENTER_Y = -PLATE_T - CAM_EDGE_GAP - ESP32_CAM_W / 2
CAM_CENTER_Z = -3.0  # lowered so the header pins clear the horn screw path
GROOVE = PCB_T + 0.15
LIP_OVERLAP = 1.5
LIP_T = 1.2
BACK_T = 3.0


def tilt_bracket() -> Part:
    hw, hl = ESP32_CAM_W / 2, ESP32_CAM_L / 2
    y_near, y_far = CAM_CENTER_Y + hw, CAM_CENTER_Y - hw
    z_bottom, z_top = CAM_CENTER_Z - hl, CAM_CENTER_Z + hl
    x_back = CAM_PCB_BACK_X - BACK_T
    x_lip = CAM_PCB_BACK_X + GROOVE
    x_front = x_lip + LIP_T
    z_span = (z_bottom - 2, z_top + 2)

    bracket = box((-8, x_front), (-PLATE_T, 0), z_span)

    pocket_z = (-HORN_POCKET_DEPTH, 0.1)
    pocket_w = MG90S_HORN_ARM_W + 2 * p.FIT_CLEARANCE
    pocket_half = MG90S_HORN_LENGTH / 2 + p.FIT_CLEARANCE - pocket_w / 2
    horn = box((-pocket_w / 2, pocket_w / 2), pocket_z, (-pocket_half, pocket_half))
    for z in (-pocket_half, pocket_half):
        horn += cylinder(pocket_w / 2, pocket_z, axis="y", at=(0, z))
    horn += cylinder(MG90S_HORN_HUB_D / 2 + 0.5, pocket_z, axis="y")
    bracket -= horn
    bracket -= cylinder(HORN_SCREW_D / 2, (-PLATE_T - 1, 1), axis="y")

    for edge, outward in ((y_near, 1), (y_far, -1)):
        rail_y = sorted((edge, edge + outward * CAM_EDGE_GAP))
        bracket += box((x_back, x_front), rail_y, z_span)
        lip_y = sorted((edge, edge - outward * LIP_OVERLAP))
        bracket += box((x_lip, x_front), lip_y, z_span)

    # Back plate only behind the top half: the header pins occupy the bottom half.
    header_top = z_bottom + ESP32_CAM_HEADER_LEN
    bracket += box(
        (x_back, CAM_PCB_BACK_X), (y_far - 0.1, y_near + 0.1), (header_top + 0.5, z_span[1])
    )
    bracket += box((CAM_PCB_BACK_X, x_front), (y_far - 0.1, y_near + 0.1), (z_span[0], z_bottom))
    return bracket
