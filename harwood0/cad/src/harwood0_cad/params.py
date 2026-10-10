"""Print settings and the rover's layout.

Printed parts and the assembly both read from here, so moving something is a
one-line edit. Purchased-part dimensions live with their models in
`harwood0_cad.hardware`. Axes: X forward, Y left, Z up; the origin is the
centre of the footprint on the ground. All units are millimetres.
"""

from harwood0_cad.hardware.battery import LIPO_H
from harwood0_cad.hardware.boards import ESP32_CAM_LENS_TIP, UNO_HEIGHT
from harwood0_cad.hardware.motors import GA25_GEARBOX_D, GA25_LENGTH
from harwood0_cad.hardware.wheels import COUPLING_L, WHEEL_D, WHEEL_W

# Printer build volume (X, Y, Z): a Bambu Lab X2D, whose auxiliary nozzle (and so any
# print using both nozzles) only reaches 235.5 mm in X. Parts must fit this smallest volume.
BUILD_VOLUME = (235.5, 256.0, 256.0)

# Extra clearance added to holes and mating faces to absorb FDM shrink/over-extrusion.
# Calibrate with the tolerance_coupon part and update, along with the insert holes below.
FIT_CLEARANCE = 0.2
# Clearance around a servo body passing through a window: larger windows print tighter
# than small holes (the first layer's squish closes them up), and the servo has to pass easily.
SERVO_FIT_CLEARANCE = 0.5

# Minimum wall thickness for structural walls (a multiple of a 0.4 mm nozzle line width).
WALL = 2.4

# Fasteners: machine screws into heat-set inserts, or through-bolted with a nut where an
# insert has no room. Insert holes are sized for common kit inserts (M2.5 x 4 mm, about
# 3.5 mm across the knurl; M3 x 4 mm, about 4.2 mm); check the maker's recommended hole,
# and calibrate with the tolerance coupon.
M3_CLEARANCE_D = 3.2 + FIT_CLEARANCE
M3_HEAD_D = 6.0
M3_INSERT_HOLE_D = 4.0
M3_INSERT_L = 4.0
M3_NUT_AF = 5.5  # across the flats
M3_NUT_T = 2.4
M2_5_CLEARANCE_D = 2.7 + FIT_CLEARANCE
M2_5_HEAD_D = 4.5
M2_5_INSERT_HOLE_D = 3.2
M2_5_INSERT_L = 4.0
M2_5_NUT_AF = 5.0
M2_5_NUT_T = 2.0
INSERT_HOLE_EXTRA = 1.0  # hole depth past the insert, for the plastic it displaces
INSERT_WALL = 1.5  # plastic left around an insert's hole
NUT_CLEARANCE = 0.2  # around a nut in a hex pocket

# The structural screws (everything but the motors' face screws, which thread into the
# gearbox, and the screws supplied with the MG90S servos). M2.5 for now; the final build
# should use M3 where docs/hardware.md#final-build-screws says, by setting this to "M3".
STRUCTURAL_SCREW = "M2.5"
(
    SCREW_CLEARANCE_D,
    SCREW_HEAD_D,
    INSERT_HOLE_D,
    INSERT_L,
    NUT_AF,
    NUT_T,
) = {
    "M2.5": (
        M2_5_CLEARANCE_D,
        M2_5_HEAD_D,
        M2_5_INSERT_HOLE_D,
        M2_5_INSERT_L,
        M2_5_NUT_AF,
        M2_5_NUT_T,
    ),
    "M3": (M3_CLEARANCE_D, M3_HEAD_D, M3_INSERT_HOLE_D, M3_INSERT_L, M3_NUT_AF, M3_NUT_T),
}[STRUCTURAL_SCREW]
INSERT_DEPTH = INSERT_L + INSERT_HOLE_EXTRA
INSERT_BOSS_D = INSERT_HOLE_D + 2 * INSERT_WALL  # smallest boss or post an insert goes in

# Body: a flat box, rounded at the nose, open on top under a removable work table.
CHASSIS_L = 240.0
CHASSIS_W = 200.0
NOSE_R = 30.0  # front corners, in plan
TAIL_R = 15.0  # rear corners, in plan
BODY_WALL_T = 3.0
FLOOR_T = 3.0
BOTTOM_EDGE_R = 3.0

# Drivetrain: four motors bolted by their gearbox faces to two lengthwise inner walls,
# each directly driving a mecanum wheel that sits in an arched well in the body side.
AXLE_Z = WHEEL_D / 2
MOTOR_X = 75.0  # half the wheelbase
FLOOR_Z = AXLE_Z - GA25_GEARBOX_D / 2 - 1.5 - FLOOR_T  # floor underside
FLOOR_TOP_Z = FLOOR_Z + FLOOR_T
MOTOR_WALL_T = 6.0
MOTOR_FACE_Y = 54.0  # inner face of each motor wall
MOTOR_WALL_Y = MOTOR_FACE_Y + MOTOR_WALL_T  # outer face of each motor wall; wells start here
assert 2 * GA25_LENGTH + 2 < 2 * MOTOR_FACE_Y, "facing motors collide"

WHEEL_GAP = 0.5  # motor wall to coupling
WHEEL_Y = MOTOR_WALL_Y + WHEEL_GAP + COUPLING_L + WHEEL_W / 2
WELL_R = WHEEL_D / 2 + 4  # arch radius around the axle
WELL_DIVIDER_T = 3.0  # walls between each well and the side bay
WELL_DIVIDER_X = MOTOR_X - WELL_R  # inner face of each divider, towards the side bay

# Heights: the chassis tray is closed by a top plate, which carries the track and frames the
# removable work table with a margin all round.
SUPPORT_Z = AXLE_Z + WELL_R + 6  # chassis wall tops, top plate underside
TOP_PLATE_T = 6.0
TOP_Z = SUPPORT_Z + TOP_PLATE_T  # body top
TABLE_T = 4.0
TABLE_MARGIN = 15.0  # top plate visible around the table, from the body edge
TABLE_MARGIN_TRACK = 22.0  # and from the track, which is wider to hold the cable channel
TABLE_LIP_W = 4.0  # ledge in the top plate's opening that the table rests on
TABLE_Z = TOP_Z - TABLE_T  # table underside; its top is flush with the body top
# Rim: a low rounded-rectangle wall on the table top that stops carried objects sliding off.
TABLE_RIM_H = 2.0  # above the table top
TABLE_RIM_W = 2.0
TABLE_RIM_INSET = 2.0  # from the table edges, and from the finger notch at the rear
TABLE_RIM_R = NOSE_R - TABLE_MARGIN - TABLE_RIM_INSET  # outer corners; concentric with the nose
assert SUPPORT_Z > FLOOR_TOP_Z + LIPO_H + 5, "battery does not fit under the top plate"
assert SUPPORT_Z > FLOOR_TOP_Z + 5 + UNO_HEIGHT + 5, "Uno does not fit under the top plate"
assert SUPPORT_Z > AXLE_Z + WHEEL_D / 2 + 3, "wheels rub the top plate"

# Track: a raised strip along the right of the top plate, carrying the arm tower's carriage.
TRACK_Y = (-(CHASSIS_W / 2 - BODY_WALL_T), -(MOTOR_WALL_Y - MOTOR_WALL_T / 2))
TRACK_FRONT_OFFSET = 20.0  # from the nose to the track's front end
TRACK_REAR_OFFSET = 20.0  # from the tail to the track's rear end
TRACK_X = (-CHASSIS_L / 2 + TRACK_REAR_OFFSET, CHASSIS_L / 2 - TRACK_FRONT_OFFSET)
TABLE_Y = (TRACK_Y[1] + TABLE_MARGIN_TRACK, CHASSIS_W / 2 - TABLE_MARGIN)

# Tower cable: a flat ribbon in a rolling loop, in the margin between the track and the table.
# Its fixed end drops into the body through the port at the front; from there it lies along
# a channel recessed into the margin, curls up and over, and runs back to a clamp at the
# carriage's rear. As the carriage moves, the curl rolls along the channel.
CABLE_CHANNEL_Y = (TRACK_Y[1] + 8.5, TRACK_Y[1] + 19.0)  # clear of the track-side snap slots
CABLE_CHANNEL_X = (-110.0, 102.0)
CABLE_CHANNEL_DEPTH = 4.0
CABLE_PORT_X = (90.0, 102.0)
CABLE_BEND_R = 5.0  # the ribbon's curl
# The ribbon: two stacked layers of jumper wire (bus and servo power, then the stepper's five).
RIBBON_WIDTH = 9.5
RIBBON_THICKNESS = 3.2

# Top plate snaps: arms rising from the chassis walls through slots in the top plate, their
# barbs clicking over its top face. Each is (x, y) on a wall's inner face, and the direction
# (degrees about Z, 0 = +X) that faces into the body from that wall. The track side snaps
# sit on the right motor wall, clear of the cable port, so their barbs pass under the carriage.
_FRONT_X, _REAR_X = CHASSIS_L / 2 - BODY_WALL_T, -CHASSIS_L / 2 + BODY_WALL_T
_LEFT_Y = CHASSIS_W / 2 - BODY_WALL_T
TOP_PLATE_SNAPS = (
    ((_FRONT_X, 40.0), 180.0),
    ((_FRONT_X, -40.0), 180.0),
    ((_REAR_X, 40.0), 0.0),
    ((_REAR_X, -40.0), 0.0),
    ((-15.0, _LEFT_Y), -90.0),
    ((15.0, _LEFT_Y), -90.0),
    *(((x, -MOTOR_FACE_Y), 90.0) for x in (-55.0, -25.0, 30.0, 60.0)),
)

# Electronics, all under the table.
BATTERY_CENTER = (0.0, 34.0)
UNO_ORIGIN = (6.6, 0.4)  # board rotated 180 deg: this is its bottom-left corner after rotation
UNO_STANDOFF_H = 5.0
BOARD_STANDOFF_D = INSERT_BOSS_D
TB6612_CENTERS = ((46.0, -18.0), (46.0, -42.0))  # front-wheel driver, rear-wheel driver
UBEC_CENTER = (0.0, 74.0)  # left side bay
ULN2003_CENTER = (0.0, -78.5)  # right side bay, under the track

# Front camera: stands on the floor, its lens in a window in the nose, nominally flush outside.
CAMERA_PCB_FRONT_X = CHASSIS_L / 2 - ESP32_CAM_LENS_TIP

# Arm tower: rides the track on a carriage. The yaw servo hangs in the tower's hood over the
# table; the arm is yaw, shoulder, elbow, and a gripper with its own camera.
CARRIAGE_L = 50.0
ARM_YAW_Y = -24.0  # yaw axis, inside the table's right edge; clears the carriage when yawed
SHOULDER_Z = 215.0  # shoulder axis height above the ground
UPPER_ARM_L = 105.0  # shoulder axis to elbow axis
FOREARM_L = 120.0  # elbow axis to the gripper fingertips
