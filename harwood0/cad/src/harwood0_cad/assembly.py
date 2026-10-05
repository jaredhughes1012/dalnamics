"""The rover as modules (chassis, work table, arm tower) and as the finished robot.

Each module is a list of printed parts and hardware placed in the global frame,
exactly where they sit on the finished robot. The arm tower takes a `Pose`.
`layout()` adds detached copies of each module beside the robot for the viewer.
Used by the renderer, the viewer, the interference and stability checks.
"""

from dataclasses import dataclass, replace

from build123d import Location, Part, Pos, Rot

from harwood0_cad import params as p
from harwood0_cad.arm import POSES, Pose, frames, jaw_travel
from harwood0_cad.arm_geometry import (
    FOREARM_T,
    GRIPPER_HORN_L,
    GRIPPER_Y,
    MG90S_MOUNT_TOP,
    PINION_Y,
    PINION_Z,
    SHOULDER_DROP,
    SHOULDER_FACE_X,
    STEPPER_FLANGE_Y,
    TRACK_TOP_Z,
    YAW_SERVO_FACE_Z,
    YAW_Y,
)
from harwood0_cad.hardware import (
    HARDWARE,
    ds3218,
    dupont_housing,
    esp32_cam,
    ga25_motor,
    lipo_3s,
    mecanum_wheel,
    mg90s,
    mg90s_horn,
    mg996r,
    pca9685,
    standard_horn,
    stepper_28byj48,
    tb6612,
    ubec,
    uln2003,
    uno_r4_wifi,
)
from harwood0_cad.hardware.battery import LIPO_MASS
from harwood0_cad.hardware.boards import (
    DUPONT_PITCH,
    ESP32_CAM_L,
    ESP32_CAM_MASS,
    PCA9685_CHANNEL_X0,
    PCA9685_HEADER_TOP,
    PCA9685_L,
    PCA9685_MASS,
    PCA9685_W,
    TB6612_MASS,
    UBEC_MASS,
    ULN2003_MASS,
    UNO_MASS,
)
from harwood0_cad.hardware.motors import BYJ_MASS, DS3218_MASS, GA25_MASS, MG90S_MASS, MG996R_MASS
from harwood0_cad.hardware.wheels import WHEEL_MASS
from harwood0_cad.parts import (
    PARTS,
    carriage,
    chassis,
    forearm,
    gripper_base,
    gripper_gear,
    gripper_jaw_front,
    gripper_jaw_rear,
    hood,
    hood_lid,
    pinion,
    table,
    top_plate,
    tower,
    tower_door,
    track_lip,
    upper_arm,
    yaw_bracket,
)
from harwood0_cad.parts.gripper import CAM_CENTER_X, CAM_FRONT_Y
from harwood0_cad.parts.tower import DRIVER_PLACE, DRIVER_SERVO_CHANNELS
from harwood0_cad.track_geometry import POCKET_X, SLOT_DEPTH, SLOT_Y

PRINTED = "#e8833a"
TABLE_COLOR = "#d9b98c"
METAL = "#aab2ba"
BLACK = "#33383d"
PCB_GREEN = "#1f6f4a"
PCB_TEAL = "#1c7c8c"
BLUE = "#2d5fa8"
HARDWARE_GREY = "#5b6770"
WHITE = "#e6e6e6"
SERVO_BLACK = "#2a2a2a"
HORN_MASS = 3.0

WHEEL_POSITIONS = {
    "front_left": (p.MOTOR_X, 1),
    "front_right": (p.MOTOR_X, -1),
    "rear_left": (-p.MOTOR_X, 1),
    "rear_right": (-p.MOTOR_X, -1),
}

# Where each detached module sits in the viewer layout, relative to its place on the robot.
LAYOUT_OFFSETS = {
    "chassis": Pos(0, -320, 0),
    "table": Pos(0, 300, -p.TABLE_Z),
    "arm tower": Pos(0, 560, -(TRACK_TOP_Z - SLOT_DEPTH)),
}

# Turn a servo model (shaft along +Z, body towards -X) so its shaft points along +X or -X,
# with its body towards -Y: how the MG90S servos sit on their links.
SHAFT_ALONG_X = Rot(90, 0, 0) * Rot(0, 90, 0)
SHAFT_ALONG_NEG_X = Rot(0, 0, 90) * Rot(-90, 0, 0)


@dataclass(frozen=True)
class Item:
    name: str
    shape: Part
    color: str
    printed: bool
    mass: float = 0.0  # grams, for hardware; printed parts are estimated from their volume

    def moved(self, location: Location) -> "Item":
        return replace(self, shape=location * self.shape)


def _side_rotation(side: int) -> Location:
    """Turns a +Z-pointing shaft to point outward on the given side (+1 left, -1 right)."""
    return Rot(-90 * side, 0, 0)


def chassis_module() -> list[Item]:
    """The body with everything inside it, the wheels, and the top plate with its track."""
    floor = p.FLOOR_TOP_Z
    lip_place = Pos(POCKET_X[0] + 0.2, SLOT_Y, p.SUPPORT_Z)
    lip_length = POCKET_X[1] - POCKET_X[0] - 0.4
    lip_turn = Pos(lip_length / 2, 0, 0) * Rot(0, 0, 180) * Pos(-lip_length / 2, 0, 0)
    camera = Pos(p.CAMERA_PCB_FRONT_X, 0, floor + ESP32_CAM_L / 2) * Rot(90, 0, 0) * Rot(0, 90, 0)
    items = [
        Item("chassis", Pos(0, 0, p.FLOOR_Z) * chassis(), PRINTED, True),
        Item("top_plate", Pos(0, 0, p.SUPPORT_Z) * top_plate(), PRINTED, True),
        Item("track_lip_left", lip_place * track_lip(), PRINTED, True),
        Item("track_lip_right", lip_place * lip_turn * track_lip(), PRINTED, True),
        Item("battery", Pos(*p.BATTERY_CENTER, floor) * lipo_3s(), BLUE, False, LIPO_MASS),
        Item("ubec", Pos(*p.UBEC_CENTER, floor) * ubec(), BLACK, False, UBEC_MASS),
        Item(
            "uno",
            Pos(*p.UNO_ORIGIN, floor + p.UNO_STANDOFF_H) * Rot(0, 0, 180) * uno_r4_wifi(),
            PCB_TEAL,
            False,
            UNO_MASS,
        ),
        Item(
            "uln2003",
            Pos(*p.ULN2003_CENTER, floor + p.UNO_STANDOFF_H) * uln2003(),
            PCB_GREEN,
            False,
            ULN2003_MASS,
        ),
        Item("camera", camera * esp32_cam(), BLACK, False, ESP32_CAM_MASS),
    ]
    for name, center in zip(("tb6612_front", "tb6612_rear"), p.TB6612_CENTERS):
        items.append(Item(name, Pos(*center, floor) * tb6612(), PCB_GREEN, False, TB6612_MASS))

    for name, (x, side) in WHEEL_POSITIONS.items():
        turn = _side_rotation(side)
        motor = Pos(x, side * p.MOTOR_FACE_Y, p.AXLE_Z) * turn * ga25_motor()
        # Front-left and rear-right share a roller hand; the other two are mirrored.
        hand = 1 if (x > 0) == (side > 0) else -1
        wheel = Pos(x, side * p.WHEEL_Y, p.AXLE_Z) * turn * mecanum_wheel(hand)
        items.append(Item(f"motor_{name}", motor, METAL, False, GA25_MASS))
        items.append(Item(f"wheel_{name}", wheel, BLACK, False, WHEEL_MASS))
    return items


def table_module() -> list[Item]:
    return [Item("table", Pos(0, 0, p.TABLE_Z) * table(), TABLE_COLOR, True)]


def _driver_plugs() -> list[tuple[str, Location, int]]:
    """Plugs on the servo driver's headers, in the board's own frame: the servo channels along
    its long edge, and the bus (GND, OE, SCL, SDA, VCC, V+) at its end."""
    plugs = []
    for k in range(DRIVER_SERVO_CHANNELS):
        x = PCA9685_CHANNEL_X0 + DUPONT_PITCH * (k + 0.5)
        plugs.append(
            (f"channel {k}", Pos(x, PCA9685_W / 2 - 4.2, PCA9685_HEADER_TOP) * Rot(0, 0, 90), 3)
        )
    bus = Pos(-PCA9685_L / 2 + 2.25, 0, PCA9685_HEADER_TOP) * Rot(0, 0, 90)
    plugs.append(("bus", bus, 6))
    return plugs


def tower_module(pose: Pose = POSES["neutral"]) -> list[Item]:
    """The carriage, tower, and arm, posed."""
    f = frames(pose)
    # The arm camera's long axis runs along X with its camera end outermost, lens facing +Y.
    camera_place = Pos(CAM_CENTER_X, CAM_FRONT_Y, 0) * Rot(0, -90, 0) * Rot(-90, 0, 0)
    stepper_place = Pos(0, STEPPER_FLANGE_Y, PINION_Z) * Rot(0, 0, -90) * Rot(0, 90, 0)
    yaw_servo = f.tower * Pos(0, YAW_Y, YAW_SERVO_FACE_Z) * Rot(0, 0, 90) * Rot(180, 0, 0)
    shoulder_servo = f.yaw * Pos(SHOULDER_FACE_X, 0, -SHOULDER_DROP) * Rot(0, -90, 0)
    # The elbow servo's tabs rest on the upper arm's back face; its shaft points back out of it.
    elbow_servo = f.upper_arm * Pos(-MG90S_MOUNT_TOP, p.UPPER_ARM_L, 0) * SHAFT_ALONG_NEG_X
    gripper_servo = f.forearm * Pos(FOREARM_T + MG90S_MOUNT_TOP, GRIPPER_Y, 0) * SHAFT_ALONG_X
    # MG90S horns are fitted with their arms along the link they drive.
    elbow_horn = elbow_servo * Rot(0, 0, pose.elbow + 90)
    gripper_horn = gripper_servo * Rot(0, 0, pose.grip + 90)
    gear_turn = Pos(0, GRIPPER_Y, 0) * Rot(pose.grip, 0, 0) * Pos(0, -GRIPPER_Y, 0)
    travel = jaw_travel(pose)
    return [
        Item("carriage", f.tower * carriage(), PRINTED, True),
        Item(
            "pinion",
            f.tower * Pos(0, PINION_Y[1], PINION_Z) * Rot(90, 0, 0) * pinion(),
            PRINTED,
            True,
        ),
        Item("track_stepper", f.tower * stepper_place * stepper_28byj48(), METAL, False, BYJ_MASS),
        Item("tower", f.tower * tower(), PRINTED, True),
        Item("tower_door", f.tower * tower_door(), PRINTED, True),
        Item("hood", f.tower * hood(), PRINTED, True),
        Item("hood_lid", f.tower * hood_lid(), PRINTED, True),
        Item("pca9685", f.tower * DRIVER_PLACE * pca9685(), PCB_GREEN, False, PCA9685_MASS),
        *(
            Item(
                f"plug {name}",
                f.tower * DRIVER_PLACE * place * dupont_housing(pins),
                BLACK,
                False,
                0.5,
            )
            for name, place, pins in _driver_plugs()
        ),
        Item("yaw_servo", yaw_servo * mg996r(), SERVO_BLACK, False, MG996R_MASS),
        Item(
            "yaw_horn", yaw_servo * Rot(0, 0, -pose.yaw) * standard_horn(), WHITE, False, HORN_MASS
        ),
        Item("yaw_bracket", f.yaw * Rot(0, 0, 180) * yaw_bracket(), PRINTED, True),
        Item("shoulder_servo", shoulder_servo * ds3218(), SERVO_BLACK, False, DS3218_MASS),
        Item(
            "shoulder_horn",
            shoulder_servo * Rot(0, 0, pose.shoulder) * standard_horn(),
            WHITE,
            False,
            HORN_MASS,
        ),
        Item("upper_arm", f.upper_arm * upper_arm(), PRINTED, True),
        Item("elbow_servo", elbow_servo * mg90s(), BLUE, False, MG90S_MASS),
        Item("elbow_horn", elbow_horn * mg90s_horn(), WHITE, False, 1.0),
        Item("forearm", f.forearm * forearm(), PRINTED, True),
        Item("arm_camera", f.forearm * camera_place * esp32_cam(), BLACK, False, ESP32_CAM_MASS),
        Item("gripper_servo", gripper_servo * mg90s(), BLUE, False, MG90S_MASS),
        Item("gripper_horn", gripper_horn * mg90s_horn(GRIPPER_HORN_L), WHITE, False, 1.0),
        Item("gripper_base", f.forearm * gripper_base(), PRINTED, True),
        Item("gripper_gear", f.forearm * gear_turn * gripper_gear(), PRINTED, True),
        Item(
            "gripper_jaw_front", f.forearm * Pos(0, 0, travel) * gripper_jaw_front(), PRINTED, True
        ),
        Item(
            "gripper_jaw_rear", f.forearm * Pos(0, 0, -travel) * gripper_jaw_rear(), PRINTED, True
        ),
    ]


def robot(pose: Pose = POSES["neutral"]) -> list[Item]:
    """The finished robot, with the arm in `pose`."""
    return chassis_module() + table_module() + tower_module(pose)


CABLE_COLORS = {True: "#d6452f", False: "#e0b030"}  # moving runs red, fixed runs yellow


def cable_items(pose: Pose = POSES["neutral"]) -> list[Item]:
    """Every cable run's path as a thin tube, posed with the arm. Not part of `robot()`."""
    from harwood0_cad.cables import RUNS, cable_shape

    return [
        Item(f"cable: {run.name}", cable_shape(run, pose), CABLE_COLORS[run.moving], False)
        for run in RUNS
    ]


def layout() -> dict[str, list[Item]]:
    """The finished robot plus a detached copy of each module beside it, and the robot's cables."""
    groups = {"robot": robot(), "cables": cable_items()}
    modules = {"chassis": chassis_module, "table": table_module, "arm tower": tower_module}
    for name, build in modules.items():
        groups[f"{name} (detached)"] = [item.moved(LAYOUT_OFFSETS[name]) for item in build()]
    return groups


def items_for(
    target: str, only: set[str] | None = None, pose: str = "neutral", cables: bool = False
) -> list[Item]:
    """Resolve a target: "assembly" (the robot, optionally filtered, optionally with its
    cables), "layout", a part, or a hardware item."""
    if target == "assembly":
        items = robot(POSES[pose])
        if only:
            items = [i for i in items if i.name in only]
        if not cables:
            return items
        # With `only`, cables are filtered by their run names too ("cable: <run>").
        wires = cable_items(POSES[pose])
        if only:
            wires = [w for w in wires if w.name in only or w.name.removeprefix("cable: ") in only]
        return items + wires
    if target == "layout":
        return [
            replace(i, name=f"{group}.{i.name}") for group, items in layout().items() for i in items
        ]
    if target in PARTS:
        return [Item(target, PARTS[target](), PRINTED, True)]
    if target in HARDWARE:
        return [Item(target, HARDWARE[target](), HARDWARE_GREY, False)]
    known = ", ".join(sorted({"assembly", "layout", *PARTS, *HARDWARE}))
    raise KeyError(f"unknown target {target!r}; known: {known}")
