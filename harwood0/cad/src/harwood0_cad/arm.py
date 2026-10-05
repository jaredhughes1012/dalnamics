"""Arm kinematics: joint frames, forward and inverse kinematics, and named poses.

A pose is the carriage's position along the track plus four joint angles, in degrees:

- yaw: about the vertical yaw axis; 0 points the arm across the table (+Y), -90 points it forward.
- shoulder: the upper arm's elevation above horizontal.
- elbow: the forearm's bend relative to the upper arm; negative bends it down.
- grip: the gripper gear's turn; each finger moves GRIPPER_GEAR_R * grip (in radians) outward.

The shoulder sits on the yaw axis, so in the arm's vertical plane the tip is a plain
two-link chain: `ik` solves for the shoulder and elbow angles that put the
fingertips at a given reach and height.
"""

import math
from dataclasses import dataclass

from build123d import Location, Pos, Rot, Vector

from harwood0_cad import params as p
from harwood0_cad.arm_geometry import (
    BRACKET_TOP_Z,
    CARRIAGE_HALF_L,
    FINGER_GAP,
    FINGER_T,
    FINGER_X,
    FOREARM_X,
    GRIPPER_GEAR_R,
    SHOULDER_DROP,
    TRACK_TOP_Z,
    UPPER_ARM_X,
    YAW_Y,
)
from harwood0_cad.track_geometry import SLOT_X, SLOT_Y

# Joint ranges (degrees). The yaw and shoulder servos turn 180 degrees.
YAW_RANGE = (-90.0, 90.0)
SHOULDER_RANGE = (-90.0, 90.0)
ELBOW_RANGE = (-170.0, 0.0)
GRIP_RANGE = (0.0, 90.0)

# The carriage's centre can travel this far along the track.
CARRIAGE_RANGE = (SLOT_X[0] + CARRIAGE_HALF_L, SLOT_X[1] - CARRIAGE_HALF_L)


@dataclass(frozen=True)
class Pose:
    carriage_x: float = 0.0
    yaw: float = 0.0
    shoulder: float = 0.0
    elbow: float = 0.0
    grip: float = 0.0

    def within_limits(self) -> bool:
        checks = (
            (self.carriage_x, CARRIAGE_RANGE),
            (self.yaw, YAW_RANGE),
            (self.shoulder, SHOULDER_RANGE),
            (self.elbow, ELBOW_RANGE),
            (self.grip, GRIP_RANGE),
        )
        return all(lo - 1e-6 <= value <= hi + 1e-6 for value, (lo, hi) in checks)


@dataclass(frozen=True)
class Frames:
    """Each part's frame: origin on its joint axis at its back (servo-side) face, the part's
    thickness along its +X, and the link running along its +Y at zero angle."""

    tower: Location  # carriage centre on the track top
    yaw: Location  # yaw axis at the bracket top face, turning with yaw
    upper_arm: Location  # shoulder axis; mirrored, so the link's thickness runs towards -X
    forearm: Location  # elbow axis; facing back towards +X


# The upper arm is mounted mirrored (back face towards +X), which this half-turn about Y does
# while keeping the link running along +Y.
_MIRROR = Rot(0, 180, 0)


def frames(pose: Pose) -> Frames:
    tower = Pos(pose.carriage_x, SLOT_Y, TRACK_TOP_Z)
    yaw = tower * Pos(0, YAW_Y, BRACKET_TOP_Z) * Rot(0, 0, pose.yaw)
    upper = yaw * Pos(UPPER_ARM_X, 0, -SHOULDER_DROP) * Rot(pose.shoulder, 0, 0) * _MIRROR
    # In the mirrored frame, +X points towards the yaw axis's -X side and +Z points down, so a
    # positive elbow (bending up) is a negative turn about this X.
    fore = upper * Pos(FOREARM_X, p.UPPER_ARM_L, 0) * Rot(-pose.elbow, 0, 0) * _MIRROR
    return Frames(tower, yaw, upper, fore)


def jaw_travel(pose: Pose) -> float:
    """How far each finger has moved out from closed (mm)."""
    return GRIPPER_GEAR_R * math.radians(pose.grip)


def grip_opening(pose: Pose) -> float:
    """Gap between the fingers (mm)."""
    return 2 * (FINGER_GAP + jaw_travel(pose))


def tip(pose: Pose) -> Vector:
    """The fingertips' midpoint, in the global frame."""
    return (frames(pose).forearm * Pos(FINGER_X + FINGER_T / 2, p.FOREARM_L, 0)).position


def shoulder_height() -> float:
    return TRACK_TOP_Z + BRACKET_TOP_Z - SHOULDER_DROP


def ik(reach: float, height: float) -> tuple[float, float] | None:
    """Shoulder and elbow angles that put the fingertips `reach` out from the yaw axis at `height`.

    Uses the elbow-up solution. Returns None if the point is out of reach.
    """
    l1, l2 = p.UPPER_ARM_L, p.FOREARM_L
    dz = height - shoulder_height()
    d = math.hypot(reach, dz)
    if d > l1 + l2 or d < abs(l1 - l2):
        return None
    to_target = math.atan2(dz, reach)
    spread = math.acos((l1**2 + d**2 - l2**2) / (2 * l1 * d))
    shoulder = to_target + spread
    elbow_x, elbow_z = l1 * math.cos(shoulder), l1 * math.sin(shoulder)
    forearm = math.atan2(dz - elbow_z, reach - elbow_x)
    return math.degrees(shoulder), math.degrees(forearm - shoulder)


def pose_for(carriage_x: float, yaw: float, reach: float, height: float, grip: float = 0.0) -> Pose:
    solution = ik(reach, height)
    if solution is None:
        raise ValueError(f"reach {reach:.0f} mm at height {height:.0f} mm is out of range")
    shoulder, elbow = solution
    return Pose(carriage_x, yaw, shoulder, elbow, grip)


TABLE_TOP_Z = p.TOP_Z
GROUND_TARGET_X = p.CHASSIS_L / 2 + 38.0  # just ahead of the nose, the gripper clear of it
GROUND_TARGET_Z = 15.0

# Named poses: the neutral display pose, the park pose the firmware assumes at power-up,
# plus the reach requirements.
POSES: dict[str, Pose] = {
    "neutral": pose_for(0.0, 0.0, 80.0, TABLE_TOP_Z + 70.0, grip=45.0),
    "park": Pose(0.0, 0.0, 45.0, -130.0, 0.0),  # must match kParkPose in firmware/lib/motion
    "table_near": pose_for(0.0, 0.0, 35.0, TABLE_TOP_Z + 8.0),
    "table_far": pose_for(0.0, 0.0, 110.0, TABLE_TOP_Z + 8.0),
    "table_diagonal": pose_for(0.0, 45.0, 90.0, TABLE_TOP_Z + 8.0),
    "table_rear": pose_for(CARRIAGE_RANGE[0], 90.0, 35.0, TABLE_TOP_Z + 8.0),
    "ground_front": pose_for(
        CARRIAGE_RANGE[1], -90.0, GROUND_TARGET_X - CARRIAGE_RANGE[1], GROUND_TARGET_Z, grip=45.0
    ),
}
