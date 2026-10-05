"""Print settings and the rover's layout.

Printed parts and the assembly both read from here, so moving something is a
one-line edit. Purchased-part dimensions live with their models in
`harwood0_cad.hardware`. Axes: X forward, Y left, Z up; the origin is the
centre of the footprint on the ground. All units are millimetres.
"""

from harwood0_cad.hardware.battery import LIPO_H
from harwood0_cad.hardware.motors import (
    BYJ_BODY_H,
    BYJ_EAR_T,
    BYJ_SHAFT_OFFSET,
    GA25_GEARBOX_D,
    GA25_LENGTH,
)
from harwood0_cad.hardware.wheels import COUPLING_L, WHEEL_D, WHEEL_W

# Printer build volume (X, Y, Z).
BUILD_VOLUME = (256.0, 256.0, 256.0)

# Extra clearance added to holes and mating faces to absorb FDM shrink/over-extrusion.
# Calibrate with the tolerance_coupon part and update.
FIT_CLEARANCE = 0.2

# Minimum wall thickness for structural walls (a multiple of a 0.4 mm nozzle line width).
WALL = 2.4

# Fasteners: M3 is the default structural fastener, self-tapped into printed pilot holes.
M3_CLEARANCE_D = 3.2 + FIT_CLEARANCE
M3_PILOT_D = 2.6
M3_HEAT_SET_D = 4.0  # typical hole diameter for an M3 x 5.7 brass heat-set insert
M3_HEAT_SET_DEPTH = 5.7

# Drivetrain: four motors bolted by their gearbox faces to the chassis side walls,
# each directly driving a mecanum wheel.
AXLE_Z = WHEEL_D / 2
MOTOR_X = 70.0  # half the wheelbase

# Chassis tray.
CHASSIS_L = 175.0
CHASSIS_W = 118.0
CHASSIS_CORNER_R = 8.0
CHASSIS_INNER_CORNER_R = 2.0  # small, so the motor gearboxes can sit tight in the corners
SIDE_WALL_T = 4.0
END_WALL_T = 3.0
FLOOR_T = 3.0
FLOOR_Z = AXLE_Z - GA25_GEARBOX_D / 2 - 1.5 - FLOOR_T  # floor underside
FLOOR_TOP_Z = FLOOR_Z + FLOOR_T
CHASSIS_TOP_Z = 55.0
CHASSIS_H = CHASSIS_TOP_Z - FLOOR_Z
MOTOR_FACE_Y = CHASSIS_W / 2 - SIDE_WALL_T  # inside face of each side wall
assert 2 * GA25_LENGTH + 4 < 2 * MOTOR_FACE_Y, "facing motors collide"
assert CHASSIS_TOP_Z > AXLE_Z + GA25_GEARBOX_D / 2, "motors poke above the chassis"
assert CHASSIS_TOP_Z > FLOOR_TOP_Z + LIPO_H + 2, "battery does not fit under the deck"

WHEEL_GAP = 1.0  # side wall to coupling
WHEEL_Y = CHASSIS_W / 2 + WHEEL_GAP + COUPLING_L + WHEEL_W / 2

# Battery sits in corner guides on the floor, held down by the deck.
BATTERY_CENTER = (0.0, 0.0)
UBEC_CENTER = (0.0, 37.5)

# Deck: a plate screwed onto the chassis walls, carrying the electronics and the camera mast.
DECK_Z = CHASSIS_TOP_Z
DECK_T = 3.0
DECK_TOP_Z = DECK_Z + DECK_T
DECK_SCREWS = tuple((x, y) for x in (-40.0, 40.0) for y in (-(MOTOR_FACE_Y - 3), MOTOR_FACE_Y - 3))
DECK_BOSS_D = 8.0

UNO_ORIGIN = (-CHASSIS_L / 2 + 4, -26.7)  # board's bottom-left corner; USB faces the rear
UNO_STANDOFF_H = 5.0
TB6612_CENTERS = ((-60.0, 42.0), (-60.0, -42.0))  # front-wheel driver, rear-wheel driver
ULN2003_CENTER = (65.5, 38.0)
BOARD_STANDOFF_D = 6.0

# Camera head: pan stepper on two pillars, pan head on its shaft, tilt servo on the pan head.
PAN_X = 45.0
STEPPER_BODY_X = PAN_X - BYJ_SHAFT_OFFSET
STEPPER_PILLAR_H = BYJ_BODY_H + 2
STEPPER_FLANGE_Z = DECK_TOP_Z + STEPPER_PILLAR_H + BYJ_EAR_T  # ear top face
PAN_HEAD_Z = STEPPER_FLANGE_Z + 3.5  # pan disc underside, clear of the ear screw heads
TILT_AXIS_H = 36.0  # tilt axis above the pan disc underside
