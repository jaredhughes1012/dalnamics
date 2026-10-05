"""Layout of the arm tower module, shared by its parts and the kinematics.

Everything here is in the tower frame: origin at the carriage centre on the track's
top face, X forward, Y left, Z up. Joint frames further out (yaw, upper arm,
forearm, jaw) are described in `harwood0_cad.arm`.
"""

from harwood0_cad import params as p
from harwood0_cad.hardware.motors import (
    BYJ_BOSS_H,
    BYJ_SHAFT_L,
    BYJ_SHAFT_OFFSET,
    MG90S_HORN_TOP,
    MG90S_TAB_T,
    MG90S_TAB_TOP,
    STD_HORN_TOP,
    STD_SERVO_TAB_T,
    STD_SERVO_TAB_TOP,
)
from harwood0_cad.track_geometry import RACK_MODULE, RACK_PITCH_Z, SLOT_Y, TRACK_T

TRACK_TOP_Z = p.SUPPORT_Z + TRACK_T  # global height of the tower frame origin
RACK_PITCH_LOCAL_Z = RACK_PITCH_Z - TRACK_T

# Carriage.
CARRIAGE_HALF_L = p.CARRIAGE_L / 2
CARRIAGE_Y = (
    -20.0,
    26.0,
)  # nothing low reaches past the track's inner edge, over the cable channel
CARRIAGE_DECK_Z = (35.0, 39.0)
CARRIAGE_SCREWS = tuple((x, y) for x in (-21.0, 21.0) for y in (-16.0, 22.0))

# Ribbon clamp: a tab off the carriage's rear end wall, over the cable channel, holding the
# ribbon's moving end. The ribbon comes down from inside the carriage through the tab's slot
# (which sits inboard of the end wall), then runs under the tab towards the curl.
RIBBON_TAB_X = (-p.CARRIAGE_L / 2 - 10.0, -p.CARRIAGE_L / 2 + 14.0)
RIBBON_TAB_Y = (CARRIAGE_Y[1] + 0.3, p.CABLE_CHANNEL_Y[1] - SLOT_Y)
RIBBON_TAB_Z = (6.0, 9.0)
RIBBON_SLOT = (
    (-p.CARRIAGE_L / 2 + 6.0, -p.CARRIAGE_L / 2 + 11.0),
    (p.CABLE_CHANNEL_Y[0] - SLOT_Y, p.CABLE_CHANNEL_Y[1] - SLOT_Y),
)

# Track drive: a pinion on the stepper shaft, meshing with the rack in the slot.
PINION_TEETH = 18
PINION_MODULE = RACK_MODULE
PINION_PITCH_R = PINION_MODULE * PINION_TEETH / 2
PINION_Z = RACK_PITCH_LOCAL_Z + PINION_PITCH_R  # pinion and stepper shaft axis
PINION_Y = (-3.0, 3.0)  # centred on the rack
STEPPER_FLANGE_Y = (
    PINION_Y[0] + BYJ_BOSS_H + BYJ_SHAFT_L
)  # ear face; the shaft tip is flush with the pinion
STEPPER_BODY_Z = PINION_Z + BYJ_SHAFT_OFFSET  # body sits above its shaft

# Yaw: the yaw servo hangs shaft-down in the hood, and the yaw bracket hangs from its horn.
YAW_Y = p.ARM_YAW_Y - SLOT_Y
SHOULDER_Z = p.SHOULDER_Z - TRACK_TOP_Z
SHOULDER_DROP = 22.0  # yaw bracket top face above the shoulder axis
BRACKET_TOP_Z = SHOULDER_Z + SHOULDER_DROP
STD_HORN_POCKET = 2.0  # depth of the pockets the disc horns sit in
MG90S_HORN_POCKET = 1.8
YAW_SERVO_FACE_Z = BRACKET_TOP_Z - STD_HORN_POCKET + STD_HORN_TOP  # yaw servo top face, facing down
HOOD_FLOOR_Z = (
    YAW_SERVO_FACE_Z - STD_SERVO_TAB_TOP + STD_SERVO_TAB_T
)  # hood floor underside; the tabs press up on it

# Shoulder, in the yaw frame (origin on the yaw axis at the bracket top face). The shoulder
# servo's shaft points -X, so the upper arm hangs on the inboard side of the yaw axis; the
# elbow and gripper servos then fold the chain back towards +X, which brings the fingertips
# close to the yaw axis's plane and keeps the arm clear of the carriage when it points forward.
SHOULDER_FACE_X = -15.0  # shoulder servo top face (must match yaw_bracket.FACE_X, mirrored)
UPPER_ARM_X = SHOULDER_FACE_X - STD_HORN_TOP + STD_HORN_POCKET  # upper arm's back face

# Link and jaw thicknesses, and how each MG90S stacks onto the link it is mounted on.
LINK_T = 6.0
FOREARM_T = 5.0
JAW_T = 4.0
MG90S_MOUNT_TOP = -MG90S_TAB_TOP + MG90S_TAB_T  # top face above the face its tabs rest on
# The elbow servo sits on the upper arm's back face with its shaft pointing out of it, so the
# forearm's back face sits this far along the upper arm frame's -X (towards the yaw axis).
FOREARM_X = -(MG90S_MOUNT_TOP + MG90S_HORN_TOP - MG90S_HORN_POCKET)
JAW_X = FOREARM_T + MG90S_MOUNT_TOP + MG90S_HORN_TOP - MG90S_HORN_POCKET  # in the forearm frame

# Gripper: a parallel rack-and-pinion gripper at the forearm's end. A gear on the gripper
# servo's horn drives two jaws in opposite directions; each jaw is a rack sliding in its own
# dovetail groove in the gripper base, with a finger reaching forward to the fingertips.
# In the forearm frame the gripper axis is at (y=GRIPPER_Y, z=0) and the jaws slide along Z.
GRIPPER_GEAR_TEETH = 18
GRIPPER_GEAR_MODULE = 1.25
GRIPPER_GEAR_R = (
    GRIPPER_GEAR_MODULE * GRIPPER_GEAR_TEETH / 2
)  # pitch radius; racks sit this far either side
GRIPPER_GEAR_X = JAW_X  # gear back face (the horn sits in a pocket there)
GRIPPER_GEAR_T = 4.0
RACK_ROOT = (
    GRIPPER_GEAR_R + 1.25 * GRIPPER_GEAR_MODULE
)  # rack body starts this far from the gripper axis
RACK_BODY_T = 6.0
RACK_LENGTH = 28.0
GRIPPER_HORN_L = (
    16.0  # the gripper servo's horn, arms trimmed to this tip to tip to fit inside the gear
)
FINGER_X = GRIPPER_GEAR_X + GRIPPER_GEAR_T + 0.5  # fingers run in a plane just in front of the gear
FINGER_T = 4.0
FINGER_W = 4.0  # at the root, tapering towards the tip
FINGER_TIP_W = 2.5
FINGER_GAP = 0.5  # each finger's inner face from the centreline, closed
FINGER_REACH = 25.0  # fingers beyond the front rack
FINGER_CURVE = 3.0  # how far each finger bows outward mid-reach; the tips still meet
GRIPPER_Y = p.FOREARM_L - RACK_ROOT - RACK_BODY_T - FINGER_REACH
GRIPPER_BASE_X = (GRIPPER_GEAR_X - 5.8, GRIPPER_GEAR_X - 0.3)  # base floor, under the jaws and gear
JAW_TONGUE_Y = RACK_ROOT + RACK_BODY_T / 2  # tongue centreline, either side of the gripper axis
