"""Part registry: every printable part is registered here by name."""

from collections.abc import Callable

from build123d import Location, Part, Rot

from harwood0_cad.parts.arm_links import forearm, upper_arm
from harwood0_cad.parts.carriage import carriage
from harwood0_cad.parts.chassis import chassis, chassis_fit_section
from harwood0_cad.parts.gripper import (
    gripper_base,
    gripper_gear,
    gripper_jaw_front,
    gripper_jaw_rear,
)
from harwood0_cad.parts.pinion import pinion
from harwood0_cad.parts.table import table
from harwood0_cad.parts.tolerance_coupon import tolerance_coupon
from harwood0_cad.parts.top_plate import top_plate
from harwood0_cad.parts.tower import hood, hood_lid, tower, tower_door
from harwood0_cad.parts.track_lip import track_lip
from harwood0_cad.parts.yaw_bracket import yaw_bracket

PARTS: dict[str, Callable[[], Part]] = {
    "chassis": chassis,
    "top_plate": top_plate,
    "table": table,
    "carriage": carriage,
    "pinion": pinion,
    "tower": tower,
    "tower_door": tower_door,
    "hood": hood,
    "hood_lid": hood_lid,
    "yaw_bracket": yaw_bracket,
    "upper_arm": upper_arm,
    "forearm": forearm,
    "gripper_base": gripper_base,
    "gripper_gear": gripper_gear,
    "gripper_jaw_front": gripper_jaw_front,
    "gripper_jaw_rear": gripper_jaw_rear,
    "track_lip": track_lip,
    "tolerance_coupon": tolerance_coupon,
    "chassis_fit_section": chassis_fit_section,
}

# Which part of the robot each part belongs to, for organising exports. Test prints are
# not part of the robot.
PART_GROUPS: dict[str, tuple[str, ...]] = {
    "body": ("chassis", "top_plate", "table", "track_lip"),
    "tower": ("carriage", "pinion", "tower", "tower_door", "hood", "hood_lid"),
    "arm": (
        "yaw_bracket",
        "upper_arm",
        "forearm",
        "gripper_base",
        "gripper_gear",
        "gripper_jaw_front",
        "gripper_jaw_rear",
    ),
    "test": ("tolerance_coupon", "chassis_fit_section"),
}
PART_GROUP = {name: group for group, names in PART_GROUPS.items() for name in names}

# Parts modelled in their assembled orientation that print better another way up.
# Export applies these; anything not listed prints as modelled.
PRINT_ROTATIONS: dict[str, Location] = {
    "chassis": Rot(0, 0, 90),  # long side along Y, where the bed is widest
    "top_plate": Rot(0, 0, 90),
    "carriage": Rot(180, 0, 0),  # deck down
    "yaw_bracket": Rot(180, 0, 0),  # top face down
    "upper_arm": Rot(0, 90, 0),  # back face down
    "forearm": Rot(0, 90, 0),
    "gripper_base": Rot(0, -90, 0),  # floor's top face down
    "gripper_gear": Rot(0, 90, 0),
    "gripper_jaw_front": Rot(0, 90, 0),
    "gripper_jaw_rear": Rot(0, 90, 0),
    "track_lip": Rot(-90, 0, 0),  # outer face down
    "tower_door": Rot(90, 0, 0),  # outer face down
}
