"""Carriage: rides the track and carries the arm tower.

Two dovetail runners slide in the track's slot. The 28BYJ-48 sits across the
track with its shaft pointing outboard through the motor plate, driving the
pinion on the rack in the slot floor. It slides in from the open inboard side
and screws to the motor plate by its ears (2x M3). Push the pinion onto the
shaft through the window in the base before fitting the carriage to the track.
The tower screws down onto the deck (4x M3). The tower's wiring comes down
through the hole in the deck, leaves by the open inboard side, and becomes the
ribbon cable, which drops through the slot in the clamp tab at the rear.

Local frame: the tower frame (origin at the carriage centre on the track's top face).
Print upside down, deck on the bed: the runners point up and the base bridges
between the end walls.
"""

from build123d import Part, Polyline, extrude, make_face

from harwood0_cad import params as p
from harwood0_cad.arm_geometry import (
    CARRIAGE_DECK_Z,
    CARRIAGE_HALF_L,
    CARRIAGE_SCREWS,
    CARRIAGE_Y,
    PINION_Y,
    PINION_Z,
    RIBBON_SLOT,
    RIBBON_TAB_X,
    RIBBON_TAB_Y,
    RIBBON_TAB_Z,
    STEPPER_BODY_Z,
    STEPPER_FLANGE_Y,
)
from harwood0_cad.hardware.motors import BYJ_BODY_D, BYJ_BODY_H, BYJ_BOSS_D, BYJ_EAR_SPACING
from harwood0_cad.shapes import box, cylinder
from harwood0_cad.track_geometry import (
    RACK_FACE_W,
    RACK_MODULE,
    RACK_PITCH_Z,
    SLOT_BOTTOM_W,
    SLOT_DEPTH,
    SLOT_TOP_W,
    TRACK_T,
)

BASE_T = 5.0
WALL_T = 4.0
MOTOR_PLATE_T = 3.5
RUNNER_CLEARANCE = 0.3
WINDOW_X = 16.0  # half-width of the base window for the pinion and stepper body
CABLE_HOLE = ((-12.0, 12.0), (-9.0, 9.0))  # through the deck, under the tower's hollow column
WIRE_NOTCH_X = (-17.0, -7.0)  # in the motor plate, beside the stepper's wire cover
WIRE_NOTCH_Z = 26.0


def _runners() -> Part:
    """Dovetail runners along the carriage's full length, with a gap where the pinion dips in."""
    x = (-CARRIAGE_HALF_L, CARRIAGE_HALF_L)
    c = RUNNER_CLEARANCE
    top, bottom = SLOT_TOP_W / 2 - c, SLOT_BOTTOM_W / 2 - c
    z_bottom = -SLOT_DEPTH + c
    profile = Polyline(
        (x[0], -bottom, z_bottom),
        (x[0], bottom, z_bottom),
        (x[0], top, 0.1),
        (x[0], -top, 0.1),
        close=True,
    )
    runner = extrude(make_face(profile), amount=x[1] - x[0], dir=(1, 0, 0))
    # Clear the rack teeth down the middle of the slot floor, and the pinion where it meshes.
    rack_tip = RACK_PITCH_Z - TRACK_T + RACK_MODULE
    runner -= box(x, (-RACK_FACE_W / 2 - c, RACK_FACE_W / 2 + c), (z_bottom - 1, rack_tip + c))
    pinion_y = (PINION_Y[0] - 0.5, PINION_Y[1] + 0.5)
    return runner - box((-WINDOW_X, WINDOW_X), pinion_y, (z_bottom - 1, 1))


def carriage() -> Part:
    hl = CARRIAGE_HALF_L
    y0, y1 = CARRIAGE_Y
    deck_top = CARRIAGE_DECK_Z[1]
    body = box((-hl, hl), (y0, y1), (0, BASE_T))
    body -= box((-WINDOW_X, WINDOW_X), (PINION_Y[0] - 1.5, y1 + 1), (-1, BASE_T + 1))
    for sx in (-1, 1):
        body += box(sorted((sx * hl, sx * (hl - WALL_T))), (y0, y1), (0, deck_top))
    body += _runners()
    body += box((-hl, hl), (y0, y0 + WALL_T), (0, deck_top))  # outboard wall
    body += box((-hl, hl), (y0, y1), CARRIAGE_DECK_Z)

    # Ribbon clamp tab off the rear end wall, over the cable channel.
    tab = box(RIBBON_TAB_X, RIBBON_TAB_Y, RIBBON_TAB_Z)
    tab += box((-hl, -hl + WALL_T), (y1 - 2.0, RIBBON_TAB_Y[1]), (RIBBON_TAB_Z[0], deck_top))
    body += tab - box(RIBBON_SLOT[0], RIBBON_SLOT[1], (RIBBON_TAB_Z[0] - 1, RIBBON_TAB_Z[1] + 1))

    plate_y = (STEPPER_FLANGE_Y - MOTOR_PLATE_T, STEPPER_FLANGE_Y)
    plate = box((-hl, hl), plate_y, (BASE_T - 0.1, deck_top))
    # Notch at the top for the tower's wiring, coming down through the deck hole.
    plate -= box(WIRE_NOTCH_X, (plate_y[0] - 1, plate_y[1] + 1), (WIRE_NOTCH_Z, deck_top + 1))
    plate -= cylinder(
        BYJ_BOSS_D / 2 + 0.5, (plate_y[0] - 1, plate_y[1] + 1), axis="y", at=(0, PINION_Z)
    )
    for x in (-BYJ_EAR_SPACING / 2, BYJ_EAR_SPACING / 2):
        plate -= cylinder(
            p.M3_PILOT_D / 2, (plate_y[0] - 1, plate_y[1] + 1), axis="y", at=(x, STEPPER_BODY_Z)
        )
    body += plate

    # Room for the stepper body between the motor plate and the deck.
    body -= cylinder(
        BYJ_BODY_D / 2 + 0.5,
        (plate_y[1], plate_y[1] + BYJ_BODY_H + 1),
        axis="y",
        at=(0, STEPPER_BODY_Z),
    )
    for x, y in CARRIAGE_SCREWS:
        body -= cylinder(p.M3_PILOT_D / 2, (CARRIAGE_DECK_Z[0] - 4, deck_top + 1), at=(x, y))
    return body - box(*CABLE_HOLE, (CARRIAGE_DECK_Z[0] - 1, deck_top + 1))
