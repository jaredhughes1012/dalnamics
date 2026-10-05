"""Drive gearmotor, pan stepper, and tilt servo."""

from build123d import Part, Rot

from harwood0_cad.shapes import box, cylinder, d_shaft, double_d_shaft

# GA25YN370 12 V / 200 RPM gearmotor (BOM R1).
GA25_GEARBOX_D = 25.0
GA25_GEARBOX_L = 21.0
GA25_CAN_D = 24.4
GA25_CAN_L = 31.0
GA25_LENGTH = GA25_GEARBOX_L + GA25_CAN_L
GA25_BOSS_D = 7.0
GA25_BOSS_L = 2.5
GA25_SHAFT_D = 4.0
GA25_SHAFT_FLAT = 3.5
GA25_SHAFT_L = 10.0  # beyond the boss
GA25_FACE_HOLE_SPACING = 17.0  # 2x M3 tapped holes either side of the shaft, along X
GA25_TERMINAL_L = 2.0


def ga25_motor() -> Part:
    """Origin at the centre of the gearbox face; shaft along +Z, body along -Z."""
    body = cylinder(GA25_GEARBOX_D / 2, (-GA25_GEARBOX_L, 0))
    body += cylinder(GA25_CAN_D / 2, (-GA25_LENGTH, -GA25_GEARBOX_L))
    for x in (-6, 6):
        body += box((x - 1.5, x + 1.5), (-0.4, 0.4), (-GA25_LENGTH - GA25_TERMINAL_L, -GA25_LENGTH))
    body += cylinder(GA25_BOSS_D / 2, (0, GA25_BOSS_L))
    body += d_shaft(GA25_SHAFT_D, GA25_SHAFT_FLAT, (GA25_BOSS_L, GA25_BOSS_L + GA25_SHAFT_L))
    for x in (-GA25_FACE_HOLE_SPACING / 2, GA25_FACE_HOLE_SPACING / 2):
        body -= cylinder(1.25, (-4, 0.1), at=(x, 0))
    return body


# 28BYJ-48 5 V geared stepper (BOM A1). The shaft is offset from the body centre.
BYJ_BODY_D = 28.0
BYJ_BODY_H = 19.0
BYJ_SHAFT_OFFSET = 8.0  # body centre sits at -X of the shaft
BYJ_EAR_SPACING = 35.0  # mounting holes, along Y
BYJ_EAR_W = 7.0
BYJ_EAR_T = 1.0
BYJ_EAR_HOLE_D = 4.2
BYJ_BOSS_D = 9.0
BYJ_BOSS_H = 1.5
BYJ_SHAFT_D = 5.0
BYJ_SHAFT_FLAT = 3.0
BYJ_SHAFT_L = 8.5  # beyond the boss
BYJ_FLAT_L = 6.0  # flats run this far down from the shaft tip
BYJ_COVER_W = 14.6
BYJ_COVER_REACH = 17.0  # wire cover's reach from the body centre, on the -X side


def stepper_28byj48(shaft_angle: float = 0.0) -> Part:
    """Origin on the shaft axis at the mounting-ear top face; shaft along +Z, body below.

    `shaft_angle` turns the output shaft (degrees) so its flats follow whatever it drives.
    """
    cx = -BYJ_SHAFT_OFFSET
    body = cylinder(BYJ_BODY_D / 2, (-BYJ_BODY_H, 0), at=(cx, 0))
    half = BYJ_EAR_SPACING / 2
    ears = box((cx - BYJ_EAR_W / 2, cx + BYJ_EAR_W / 2), (-half, half), (-BYJ_EAR_T, 0))
    for y in (-half, half):
        ears += cylinder(BYJ_EAR_W / 2, (-BYJ_EAR_T, 0), at=(cx, y))
        ears -= cylinder(BYJ_EAR_HOLE_D / 2, (-BYJ_EAR_T - 1, 1), at=(cx, y))
    body += ears
    body += box(
        (cx - BYJ_COVER_REACH, cx - BYJ_BODY_D / 2 + 3),
        (-BYJ_COVER_W / 2, BYJ_COVER_W / 2),
        (-BYJ_BODY_H + 2, -1),
    )
    body += cylinder(BYJ_BOSS_D / 2, (0, BYJ_BOSS_H))
    tip = BYJ_BOSS_H + BYJ_SHAFT_L
    shaft = double_d_shaft(
        BYJ_SHAFT_D, BYJ_SHAFT_FLAT, (BYJ_BOSS_H, tip), (tip - BYJ_FLAT_L, tip + 1)
    )
    return body + Rot(0, 0, shaft_angle) * shaft


# MG90S metal-gear micro servo (BOM R3/A5).
MG90S_BODY_L = 22.8
MG90S_BODY_W = 12.2
MG90S_BODY_H = 22.5  # base to top face, excluding the gear boss
MG90S_SHAFT_OFFSET = 5.4  # body centre sits at -X of the output shaft
MG90S_TAB_SPAN = 32.5
MG90S_TAB_T = 2.5
MG90S_TAB_TOP = -4.1  # tab top face, below the body top face
MG90S_TAB_HOLE_SPACING = 27.8
MG90S_TAB_HOLE_D = 2.0
MG90S_GEAR_BOSS_D = 11.8
MG90S_GEAR_BOSS_H = 4.0
MG90S_SPLINE_D = 4.8
MG90S_SPLINE_H = 3.0

# Double-arm horn supplied with the servo, seated on the spline.
MG90S_HORN_HUB_D = 7.0
MG90S_HORN_LENGTH = 31.0  # tip to tip, along Y
MG90S_HORN_ARM_W = 5.0
MG90S_HORN_ARM_T = 1.6
MG90S_HORN_TOP = MG90S_GEAR_BOSS_H + 4.0  # horn top face above the body top face


def mg90s() -> Part:
    """Origin on the output shaft axis at the body top face; shaft along +Z, body below.

    Body length is along X, width along Y.
    """
    cx = -MG90S_SHAFT_OFFSET
    hl, hw = MG90S_BODY_L / 2, MG90S_BODY_W / 2
    body = box((cx - hl, cx + hl), (-hw, hw), (-MG90S_BODY_H, 0))
    tab_z = (MG90S_TAB_TOP - MG90S_TAB_T, MG90S_TAB_TOP)
    tabs = box((cx - MG90S_TAB_SPAN / 2, cx + MG90S_TAB_SPAN / 2), (-hw, hw), tab_z)
    for x in (-MG90S_TAB_HOLE_SPACING / 2, MG90S_TAB_HOLE_SPACING / 2):
        tabs -= cylinder(MG90S_TAB_HOLE_D / 2, (tab_z[0] - 1, tab_z[1] + 1), at=(cx + x, 0))
    body += tabs
    body += cylinder(MG90S_GEAR_BOSS_D / 2, (0, MG90S_GEAR_BOSS_H))
    body += cylinder(MG90S_SPLINE_D / 2, (MG90S_GEAR_BOSS_H, MG90S_GEAR_BOSS_H + MG90S_SPLINE_H))
    return body


def mg90s_horn() -> Part:
    """In the servo's frame (see mg90s): hub on the spline, arms along Y."""
    top = MG90S_HORN_TOP
    horn = cylinder(MG90S_HORN_HUB_D / 2, (MG90S_GEAR_BOSS_H, top))
    half = MG90S_HORN_LENGTH / 2 - MG90S_HORN_ARM_W / 2
    arm_z = (top - MG90S_HORN_ARM_T, top)
    horn += box((-MG90S_HORN_ARM_W / 2, MG90S_HORN_ARM_W / 2), (-half, half), arm_z)
    for y in (-half, half):
        horn += cylinder(MG90S_HORN_ARM_W / 2, arm_z, at=(0, y))
    return horn
