"""Circuit boards: motion controller, motor and stepper drivers, camera, and power regulator."""

from build123d import Part

from harwood0_cad.shapes import box, cylinder

PCB_T = 1.6

# Arduino Uno R4 WiFi (BOM S1): standard Uno outline and mounting holes.
UNO_L = 68.6
UNO_W = 53.4
UNO_HOLES = ((13.97, 2.54), (15.24, 50.8), (66.04, 7.62), (66.04, 35.56))
UNO_HOLE_D = 3.2
UNO_HEIGHT = 12.5  # PCB bottom to top of the headers and barrel jack


def uno_r4_wifi() -> Part:
    """Origin at the PCB's bottom-left corner (USB/barrel-jack edge at X=0), PCB bottom at Z=0."""
    top = PCB_T
    board = box((0, UNO_L), (0, UNO_W), (0, top))
    for x, y in UNO_HOLES:
        board -= cylinder(UNO_HOLE_D / 2, (-1, top + 1), at=(x, y))
    board += box((-1.5, 6.0), (33.0, 42.0), (top, top + 3.3))  # USB-C
    board += box((-1.9, 12.1), (3.3, 12.3), (top, top + 11.0))  # barrel jack
    board += box((17.5, 65.5), (50.3, 52.8), (top, top + 8.5))  # digital headers
    board += box((27.5, 64.5), (0.6, 3.1), (top, top + 8.5))  # power + analog headers
    board += box((20.0, 32.0), (38.0, 48.0), (top, top + 3.0))  # ESP32-S3 module
    board += box((36.0, 58.0), (14.0, 34.0), (top, top + 1.0))  # LED matrix
    return board


# TB6612FNG dual motor driver breakout (BOM R2), headers soldered pins-up.
TB6612_SIZE = 20.3
TB6612_HEIGHT = PCB_T + 8.5


def tb6612() -> Part:
    """Origin at the PCB centre, PCB bottom at Z=0; header rows along the X edges."""
    h = TB6612_SIZE / 2
    board = box((-h, h), (-h, h), (0, PCB_T))
    for x in (-h + 0.3, h - 2.8):
        board += box((x, x + 2.5), (-h, h), (PCB_T, TB6612_HEIGHT))
    board += box((-3, 3), (-3.5, 3.5), (PCB_T, PCB_T + 1.2))
    return board


# ULN2003 stepper driver board (BOM A2).
ULN2003_L = 35.0
ULN2003_W = 32.0
ULN2003_HOLE_INSET = 2.5
ULN2003_HOLE_D = 3.0


def uln2003() -> Part:
    """Origin at the PCB centre, PCB bottom at Z=0; stepper connector on the +Y edge."""
    hl, hw = ULN2003_L / 2, ULN2003_W / 2
    board = box((-hl, hl), (-hw, hw), (0, PCB_T))
    for x in (-hl + ULN2003_HOLE_INSET, hl - ULN2003_HOLE_INSET):
        for y in (-hw + ULN2003_HOLE_INSET, hw - ULN2003_HOLE_INSET):
            board -= cylinder(ULN2003_HOLE_D / 2, (-1, PCB_T + 1), at=(x, y))
    board += box((-9.75, 9.75), (-3.25, 3.25), (PCB_T, PCB_T + 4.0))  # ULN2003 DIP
    board += box((-6.25, 6.25), (hw - 7, hw - 1), (PCB_T, PCB_T + 7.0))  # JST-XH motor socket
    board += box((-hl + 1, -hl + 3.5), (-6, 6), (PCB_T, PCB_T + 8.5))  # IN1-IN4 header
    return board


# AI-Thinker ESP32-CAM with OV2640 (BOM A8).
ESP32_CAM_W = 27.0
ESP32_CAM_L = 40.5
ESP32_CAM_HEADER_PITCH = 22.86  # between the two header rows
ESP32_CAM_HEADER_LEN = 20.32  # 8 pins, starting at the -Y edge
ESP32_CAM_HEADER_DEPTH = 8.5  # header plastic plus pins, behind the PCB


def esp32_cam() -> Part:
    """Origin at the PCB centre with the front (camera) face at Z=0 facing +Z.

    Long axis along Y with the camera towards +Y; header pins stick out the back (-Z).
    """
    hw, hl = ESP32_CAM_W / 2, ESP32_CAM_L / 2
    board = box((-hw, hw), (-hl, hl), (-PCB_T, 0))
    board += box((-9, 9), (-2, hl), (0, 3.2))  # ESP32 module shield
    board += box((-4.25, 4.25), (4.5, 13.0), (3.2, 6.2))  # camera module
    board += cylinder(3.5, (6.2, 10.0), at=(0, 8.75))  # lens
    board += box((-7, 7), (-hl + 1, -hl + 15), (0, 2.0))  # microSD slot
    header_y = (-hl, -hl + ESP32_CAM_HEADER_LEN)
    for x in (-ESP32_CAM_HEADER_PITCH / 2, ESP32_CAM_HEADER_PITCH / 2):
        board += box((x - 1.25, x + 1.25), header_y, (-PCB_T - ESP32_CAM_HEADER_DEPTH, -PCB_T))
    return board


# 5-6 V UBEC (BOM S2), supplying the servo, stepper, and camera.
UBEC_L = 45.0
UBEC_W = 25.0
UBEC_H = 10.0


def ubec() -> Part:
    """Origin at the bottom centre; long axis along X."""
    body = box((-UBEC_L / 2, UBEC_L / 2), (-UBEC_W / 2, UBEC_W / 2), (0, UBEC_H))
    for y in (-4, 4):
        body += cylinder(1.2, (-8, 0), axis="x", at=(y, UBEC_H / 2))
    return body
