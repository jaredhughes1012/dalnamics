"""The full rover: printed parts and hardware placed in the global frame.

Used by the renderer, the ocp_vscode viewer, and the interference tests. The
camera head can be posed with `pan` and `tilt` (degrees) to check clearances
across its range of motion.
"""

from dataclasses import dataclass

from build123d import Location, Part, Pos, Rot

from harwood0_cad import params as p
from harwood0_cad.hardware import (
    HARDWARE,
    esp32_cam,
    ga25_motor,
    lipo_3s,
    mecanum_wheel,
    mg90s,
    mg90s_horn,
    stepper_28byj48,
    tb6612,
    ubec,
    uln2003,
    uno_r4_wifi,
)
from harwood0_cad.hardware.boards import PCB_T
from harwood0_cad.hardware.motors import MG90S_HORN_TOP
from harwood0_cad.parts import PARTS, chassis, deck, pan_head, tilt_bracket
from harwood0_cad.parts.pan_head import SERVO_TOP_Y
from harwood0_cad.parts.tilt_bracket import (
    CAM_CENTER_Y,
    CAM_CENTER_Z,
    CAM_PCB_BACK_X,
    HORN_POCKET_DEPTH,
)

PRINTED = "#e8833a"
METAL = "#aab2ba"
BLACK = "#33383d"
PCB_GREEN = "#1f6f4a"
PCB_TEAL = "#1c7c8c"
BLUE = "#2d5fa8"
WHITE = "#e6e6e6"
HARDWARE_GREY = "#5b6770"

WHEEL_POSITIONS = {
    "front_left": (p.MOTOR_X, 1),
    "front_right": (p.MOTOR_X, -1),
    "rear_left": (-p.MOTOR_X, 1),
    "rear_right": (-p.MOTOR_X, -1),
}


@dataclass(frozen=True)
class Item:
    name: str
    shape: Part
    color: str
    printed: bool


def _side_rotation(side: int) -> Location:
    """Turns a +Z-pointing shaft to point outward on the given side (+1 left, -1 right)."""
    return Rot(-90 * side, 0, 0)


def assembly(pan: float = 0.0, tilt: float = 0.0) -> list[Item]:
    items = [
        Item("chassis", Pos(0, 0, p.FLOOR_Z) * chassis(), PRINTED, True),
        Item("deck", Pos(0, 0, p.DECK_Z) * deck(), PRINTED, True),
        Item("battery", Pos(*p.BATTERY_CENTER, p.FLOOR_TOP_Z) * lipo_3s(), BLUE, False),
        Item("ubec", Pos(*p.UBEC_CENTER, p.FLOOR_TOP_Z) * ubec(), BLACK, False),
        Item(
            "uno",
            Pos(*p.UNO_ORIGIN, p.DECK_TOP_Z + p.UNO_STANDOFF_H) * uno_r4_wifi(),
            PCB_TEAL,
            False,
        ),
        Item(
            "uln2003",
            Pos(*p.ULN2003_CENTER, p.DECK_TOP_Z + p.UNO_STANDOFF_H) * uln2003(),
            PCB_GREEN,
            False,
        ),
        Item(
            "stepper",
            Pos(p.PAN_X, 0, p.STEPPER_FLANGE_Z) * stepper_28byj48(shaft_angle=pan),
            METAL,
            False,
        ),
    ]
    for name, center in zip(("tb6612_front", "tb6612_rear"), p.TB6612_CENTERS):
        items.append(Item(name, Pos(*center, p.DECK_TOP_Z) * tb6612(), PCB_GREEN, False))

    for name, (x, side) in WHEEL_POSITIONS.items():
        turn = _side_rotation(side)
        motor = Pos(x, side * p.MOTOR_FACE_Y, p.AXLE_Z) * turn * ga25_motor()
        # Front-left and rear-right share a roller hand; the other two are mirrored.
        hand = 1 if (x > 0) == (side > 0) else -1
        wheel = Pos(x, side * p.WHEEL_Y, p.AXLE_Z) * turn * mecanum_wheel(hand)
        items.append(Item(f"motor_{name}", motor, METAL, False))
        items.append(Item(f"wheel_{name}", wheel, BLACK, False))

    head = Pos(p.PAN_X, 0, p.PAN_HEAD_Z) * Rot(0, 0, pan)
    servo_frame = head * Pos(0, SERVO_TOP_Y, p.TILT_AXIS_H) * Rot(90, 0, 0)
    bracket_y = SERVO_TOP_Y - MG90S_HORN_TOP + HORN_POCKET_DEPTH
    bracket_frame = head * Pos(0, bracket_y, p.TILT_AXIS_H) * Rot(0, -tilt, 0)
    camera = Pos(CAM_PCB_BACK_X + PCB_T, CAM_CENTER_Y, CAM_CENTER_Z) * Rot(90, 0, 0) * Rot(0, 90, 0)
    items += [
        Item("pan_head", head * pan_head(), PRINTED, True),
        Item("tilt_servo", servo_frame * mg90s(), BLUE, False),
        Item("tilt_horn", servo_frame * Rot(0, 0, tilt) * mg90s_horn(), WHITE, False),
        Item("tilt_bracket", bracket_frame * tilt_bracket(), PRINTED, True),
        Item("camera", bracket_frame * camera * esp32_cam(), BLACK, False),
    ]
    return items


def items_for(
    target: str, pan: float = 0.0, tilt: float = 0.0, only: set[str] | None = None
) -> list[Item]:
    """Resolve a target name: "assembly" (optionally filtered), a printed part, or a hardware item."""
    if target == "assembly":
        items = assembly(pan=pan, tilt=tilt)
        return [i for i in items if i.name in only] if only else items
    if target in PARTS:
        return [Item(target, PARTS[target](), PRINTED, True)]
    if target in HARDWARE:
        return [Item(target, HARDWARE[target](), HARDWARE_GREY, False)]
    known = ", ".join(sorted({"assembly", *PARTS, *HARDWARE}))
    raise KeyError(f"unknown target {target!r}; known: {known}")
