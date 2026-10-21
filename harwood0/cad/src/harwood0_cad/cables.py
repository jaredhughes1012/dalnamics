"""Cable routing: every wire run as a path through the robot, with the length each one needs.

Each run is a list of waypoints, each pinned to the part it is fixed to (the body, the
tower, the yaw bracket, or an arm link), so a run's path follows the robot as it moves.
The tower's wiring reaches the body as a flat ribbon in a rolling loop along the cable
channel; its path is worked out from the carriage's position.

`harwood0-cables` sweeps the arm through its whole range and reports, for each run, the
longest path, the length to cut (with slack and room for connectors), and whether a
part's own lead is long enough or needs extending.

    uv run harwood0-cables
"""

import itertools
import math
from collections.abc import Callable
from dataclasses import dataclass

from build123d import Compound, Part, Pos, Vector

from harwood0_cad import params as p
from harwood0_cad.arm import (
    CARRIAGE_RANGE,
    ELBOW_RANGE,
    GRIP_RANGE,
    SHOULDER_RANGE,
    YAW_RANGE,
    Frames,
    Pose,
    frames,
)
from harwood0_cad.arm_geometry import (
    FOREARM_X,
    GRIPPER_Y,
    RIBBON_SLOT,
    SHOULDER_DROP,
    UPPER_ARM_X,
    YAW_SERVO_FACE_Z,
)
from harwood0_cad.hardware.boards import (
    DUPONT_L,
    DUPONT_PITCH,
    PCA9685_CHANNEL_X0,
    PCA9685_HEADER_TOP,
    PCA9685_L,
    PCA9685_W,
    UBEC_L,
)
from harwood0_cad.parts.arm_links import FOREARM_CLIPS, UPPER_ARM_CLIPS
from harwood0_cad.parts.gripper import CAM_FRONT_Y
from harwood0_cad.parts.tower import (
    ARM_CABLE_HOLE,
    COLUMN_OUTBOARD,
    COLUMN_PASS,
    COLUMN_WALL,
    DRIVER_PLACE,
    HOOD_FLOOR_Z,
    YAW_SERVO_BODY_Y,
)
from harwood0_cad.parts.yaw_bracket import BACK_X, TAB_FACE_X
from harwood0_cad.shapes import cylinder

SLACK = 1.10  # extra length over the longest path, for routing that is never quite straight
CONNECTOR_ALLOWANCE = 20.0  # per end, for crimps or solder joints and strain relief
WIRE_D = 1.4  # a jumper or servo-lead conductor, insulated
POWER_WIRE_D = 1.9  # 22 AWG silicone, for the servo supply
BUNDLE_PACKING = 1.15  # a round bundle of n wires is about this * sqrt(n) wires across


def bundle_d(wires: int, wire_d: float = WIRE_D) -> float:
    return wire_d * math.sqrt(wires) * BUNDLE_PACKING


Point = tuple[float, float, float]
Anchor = tuple[str, Point]  # (frame name, point in that frame)


@dataclass(frozen=True)
class Run:
    name: str
    route: str  # where it goes, for people
    wires: int
    path: Callable[[Pose], list[Vector]]
    lead: float | None = None  # length of the part's own lead, if it comes with one (mm)
    moving: bool = False  # crosses a joint or the track
    diameter: float | None = None  # overall thickness; a round bundle of `wires` if not given
    check_only: bool = False  # a bundle of other runs, modelled only to check it has room

    @property
    def thickness(self) -> float:
        return self.diameter if self.diameter is not None else bundle_d(self.wires)


def _resolve(f: Frames, anchors: list[Anchor]) -> list[Vector]:
    lookup = {"tower": f.tower, "yaw": f.yaw, "upper_arm": f.upper_arm, "forearm": f.forearm}
    points = []
    for frame, (x, y, z) in anchors:
        if frame == "body":
            points.append(Vector(x, y, z))
        else:
            points.append((lookup[frame] * Pos(x, y, z)).position)
    return points


def _anchored(*anchors: Anchor) -> Callable[[Pose], list[Vector]]:
    return lambda pose: _resolve(frames(pose), list(anchors))


# Waypoints shared by several runs.
_CHANNEL_Y = sum(p.CABLE_CHANNEL_Y) / 2
_LOWER_Z = (
    p.TOP_Z - p.CABLE_CHANNEL_DEPTH + p.RIBBON_THICKNESS / 2 + 0.2
)  # ribbon lying in the channel
_UPPER_Z = _LOWER_Z + 2 * p.CABLE_BEND_R  # ribbon's upper run, just under the clamp tab
_PORT_X = sum(p.CABLE_PORT_X) / 2
_HOOD_HOLE_Y = sum(ARM_CABLE_HOLE[1]) / 2
_TAB_X = sum(RIBBON_SLOT[0]) / 2
_TAB_Y = sum(RIBBON_SLOT[1]) / 2


# The tower's column and hood (tower frame). The servo driver stands inside the column with
# its plugs facing the door: the arm's leads come down in a bundle in front of the plugs,
# and each one turns in to its own plug.
def _driver_point(x: float, y: float, z: float) -> Point:
    """A point on the servo driver, from its own frame into the tower frame."""
    v = (DRIVER_PLACE * Pos(x, y, z)).position
    return (v.X, v.Y, v.Z)


def _plug_end(channel: int) -> Point:
    """Where a servo channel's lead leaves its plug."""
    x = PCA9685_CHANNEL_X0 + DUPONT_PITCH * (channel + 0.5)
    return _driver_point(x, PCA9685_W / 2 - 4.2, PCA9685_HEADER_TOP + DUPONT_L + 0.5)


_BUS_PLUG_END = _driver_point(-PCA9685_L / 2 + 2.25, 0.0, PCA9685_HEADER_TOP + DUPONT_L + 2.0)
_DOOR_INSIDE = COLUMN_OUTBOARD + COLUMN_WALL
_BUNDLE_Y = (
    _plug_end(0)[1] + _DOOR_INSIDE
) / 2  # the arm's leads run down between the plugs and the door
_COLUMN_TOP: Anchor = ("tower", (0.0, sum(COLUMN_PASS[1]) / 2, HOOD_FLOOR_Z + 8.0))
_IN_FRONT_HIGH: Anchor = ("tower", (0.0, _BUNDLE_Y, HOOD_FLOOR_Z - 15.0))
_HOOD_HOLE_ABOVE: Anchor = ("tower", (0.0, _HOOD_HOLE_Y, HOOD_FLOOR_Z + 8.0))
_HOOD_HOLE_BELOW: Anchor = ("tower", (0.0, _HOOD_HOLE_Y, HOOD_FLOOR_Z - 6.0))


def _down_column(channel: int) -> list[Anchor]:
    """Through the hood floor's pass, down the column in front of the plugs, and in to a plug."""
    x, y, z = _plug_end(channel)
    return [
        _COLUMN_TOP,
        _IN_FRONT_HIGH,
        ("tower", (x / 2, _BUNDLE_Y, z + 10.0)),
        ("tower", (x, _BUNDLE_Y, z + 4.0)),
        ("tower", (x, y, z)),
    ]


# The yaw bracket in the yaw frame, where it is turned half a turn: its open back, and the face
# of its tab plate on the shoulder side.
_BEHIND_BRACKET_X = -BACK_X + 2.0
_BRACKET_TAB_FACE_X = -TAB_FACE_X

# Over the yaw bracket to the hood (yaw frame): above the bracket's top plate and below the
# yaw servo, beside the yaw axis so the loop into the hood stays short as the arm yaws.
_BRACKET_TOP: Anchor = ("yaw", (_BEHIND_BRACKET_X, 17.0, 3.0))
_UP_TO_HOOD = [_BRACKET_TOP, _HOOD_HOLE_BELOW, _HOOD_HOLE_ABOVE]

# Joints are crossed on their axes, where a point does not move as the joint turns, then the
# wires pass the link's plane on the side it never swings to: behind the shoulder (the upper
# arm only ever points across or up and down, never back), and below the elbow.
# The crossing behind the shoulder is kept as close to the yaw axis as the upper arm allows, so
# it clears the column as the arm yaws.
_SHOULDER_OUTBOARD = 9.0  # beyond the upper arm's thickness, in its frame
_SHOULDER_AXIS_X = UPPER_ARM_X - _SHOULDER_OUTBOARD  # in the yaw frame
_BEHIND_SHOULDER_Y = -18.0  # just outside the shoulder disc
_SHOULDER_CROSSING: list[Anchor] = [
    ("upper_arm", (_SHOULDER_OUTBOARD, 0.0, 0.0)),
    ("yaw", (_SHOULDER_AXIS_X, _BEHIND_SHOULDER_Y, -SHOULDER_DROP)),
    ("yaw", (_BEHIND_BRACKET_X, _BEHIND_SHOULDER_Y, -SHOULDER_DROP)),
]
_ELBOW_CROSSING: list[Anchor] = [
    ("forearm", (9.0, 0.0, 0.0)),
    ("upper_arm", (FOREARM_X - 9.0, p.UPPER_ARM_L, 0.0)),
    ("upper_arm", (FOREARM_X - 9.0, p.UPPER_ARM_L, -20.0)),
    ("upper_arm", (7.5, p.UPPER_ARM_L - 10.0, -20.0)),
]


def _clips(frame: str, ys: tuple[float, ...], x: float, z: float) -> list[Anchor]:
    """Through each wire clip in turn, from the far end of the link towards its joint, entering
    and leaving each clip along the link."""
    anchors: list[Anchor] = []
    for y in sorted(ys, reverse=True):
        anchors += [(frame, (x, y + 6.0, z)), (frame, (x, y, z)), (frame, (x, y - 6.0, z))]
    return anchors


_UPPER_ARM_TO_HOOD: list[Anchor] = [
    *_clips("upper_arm", UPPER_ARM_CLIPS, 7.5, -12.0),
    *_SHOULDER_CROSSING,
    *_UP_TO_HOOD,
]
_FOREARM_TO_HOOD: list[Anchor] = [
    *_clips("forearm", FOREARM_CLIPS, 7.0, 12.0),
    ("forearm", (9.0, 6.0, 6.0)),
    *_ELBOW_CROSSING,
    *_UPPER_ARM_TO_HOOD,
]

# Servo driver channels.
YAW_CHANNEL, SHOULDER_CHANNEL, ELBOW_CHANNEL, GRIPPER_CHANNEL, CAMERA_CHANNEL = range(5)

# In the body (global): through the cable port, across the centre bay above the motors, and
# through the motor walls' wire holes (entering and leaving square to the wall).
_ABOVE_ELECTRONICS_Z = p.SUPPORT_Z - 28.0  # clear of the motors, battery, and Uno headers
_WALL_HOLE_Z = p.SUPPORT_Z - 12.0


def _wall_hole(side: int, from_centre: bool) -> list[Anchor]:
    """Through the left (+1) or right (-1) motor wall's wire hole, from the centre bay or into it."""
    mid = side * (p.MOTOR_WALL_Y - p.MOTOR_WALL_T / 2)
    path = [
        ("body", (0.0, mid - side * 8.0, _WALL_HOLE_Z)),
        ("body", (0.0, mid, _WALL_HOLE_Z)),
        ("body", (0.0, mid + side * 8.0, _WALL_HOLE_Z)),
    ]
    return path if from_centre else list(reversed(path))


def _over(x: float, y: float) -> Anchor:
    return ("body", (x, y, _ABOVE_ELECTRONICS_Z))


_PORT_BELOW: Anchor = ("body", (_PORT_X, _CHANNEL_Y, p.SUPPORT_Z - 6.0))
_OVER_FRONT_MOTORS: Anchor = _over(55.0, -40.0)
_ULN_SOCKET: Anchor = ("body", (0.0, p.ULN2003_CENTER[1] + 12.0, p.FLOOR_TOP_Z + 14.0))
_ULN_INPUTS: Anchor = ("body", (-15.0, p.ULN2003_CENTER[1], p.FLOOR_TOP_Z + 14.0))
_UBEC_LEADS: Anchor = (
    "body",
    (p.UBEC_CENTER[0] - UBEC_L / 2 - 2.0, p.UBEC_CENTER[1], p.FLOOR_TOP_Z + 5.0),
)
_UNO_DIGITAL: Anchor = ("body", (-35.0, -51.0, p.FLOOR_TOP_Z + 18.0))
_UNO_ANALOG: Anchor = ("body", (-30.0, -1.5, p.FLOOR_TOP_Z + 18.0))
_UNO_I2C: Anchor = ("body", (-10.0, -48.0, p.FLOOR_TOP_Z + 18.0))
_TB_FRONT: Anchor = ("body", (*p.TB6612_CENTERS[0], p.FLOOR_TOP_Z + 10.0))
_TB_REAR: Anchor = ("body", (*p.TB6612_CENTERS[1], p.FLOOR_TOP_Z + 10.0))
_NOSE_CAMERA: Anchor = ("body", (p.CAMERA_PCB_FRONT_X - 12.0, 0.0, p.FLOOR_TOP_Z + 18.0))


def _ribbon(pose: Pose) -> list[Vector]:
    """The rolling loop, from under the carriage's clamp tab to the cable port.

    The ribbon's length is fixed, chosen so the curl stays inside the channel at the
    carriage's rearmost position; the curl rolls forward as the carriage does.
    """
    x_tab = pose.carriage_x + _TAB_X
    x_tab_min = CARRIAGE_RANGE[0] + _TAB_X
    curl_min = p.CABLE_CHANNEL_X[0] + p.CABLE_BEND_R + 2.0
    straight = (x_tab_min - curl_min) + (_PORT_X - curl_min)
    curl_x = (x_tab + _PORT_X - straight) / 2
    y = _CHANNEL_Y
    points = [Vector(x_tab, y, _UPPER_Z)]
    for i in range(9):
        a = math.pi / 2 + math.pi * i / 8
        points.append(
            Vector(
                curl_x + p.CABLE_BEND_R * math.cos(a),
                y,
                _LOWER_Z + p.CABLE_BEND_R * (1 + math.sin(a)),
            )
        )
    return points + [Vector(_PORT_X, y, _LOWER_Z)]


# Down through the deck, between the stepper and the rear end wall, out of the open side,
# and through the clamp tab's slot (tower frame).
_THROUGH_CARRIAGE: list[Anchor] = [
    ("tower", (0.0, 0.0, 45.0)),
    ("tower", (-10.0, 2.0, 37.0)),
    ("tower", (-11.0, 5.25, 30.0)),  # through the motor plate's wire notch
    ("tower", (-17.5, 10.0, 28.0)),
    ("tower", (-17.5, 24.0, 18.0)),
    ("tower", (_TAB_X, _TAB_Y, 13.0)),
]


def _bundle_to_port(pose: Pose) -> list[Vector]:
    """From the servo driver's bus plug down through the carriage and along the ribbon."""
    x, y, z = _BUS_PLUG_END
    down = [
        ("tower", (x, y, z)),
        ("tower", (x, _BUNDLE_Y, z - 6.0)),
        ("tower", (0.0, _BUNDLE_Y + 3.0, 50.0)),
    ]
    tower = _resolve(frames(pose), [*down, *_THROUGH_CARRIAGE])
    return tower + _ribbon(pose) + [Vector(*_PORT_BELOW[1])]


def _stepper_to_port(pose: Pose) -> list[Vector]:
    tower = _resolve(
        frames(pose),
        [("tower", (0.0, 16.5, 33.0)), ("tower", (-10.0, 16.0, 31.0)), *_THROUGH_CARRIAGE[4:]],
    )
    return tower + _ribbon(pose) + [Vector(*_PORT_BELOW[1])]


def _then(
    first: Callable[[Pose], list[Vector]], *anchors: Anchor
) -> Callable[[Pose], list[Vector]]:
    return lambda pose: first(pose) + [Vector(*a[1]) for a in anchors]


def _motor(name: str, x: float, side: int) -> Run:
    front = x > 0
    return Run(
        f"motor {name}",
        f"from the motor's tabs, up and over the battery and Uno, to the {'front' if front else 'rear'} TB6612",
        2,
        _anchored(
            ("body", (x, 0.0, p.AXLE_Z)),
            _over(x - 15.0 * (1 if front else -1), 0.0),
            _over(40.0, -30.0 if front else -45.0),
            _TB_FRONT if front else _TB_REAR,
        ),
    )


RUNS: tuple[Run, ...] = (
    # Arm servos and camera, to the servo driver on the tower.
    Run(
        "yaw servo",
        "inside the hood, through the pass into the column, to the servo driver",
        3,
        _anchored(
            # Up from the notch at the shaft end, back over the servo under the lid.
            ("tower", (0.0, YAW_SERVO_BODY_Y + 21.5, YAW_SERVO_FACE_Z + 15.0)),
            ("tower", (0.0, YAW_SERVO_BODY_Y + 22.5, YAW_SERVO_FACE_Z + 38.5)),
            ("tower", (0.0, YAW_SERVO_BODY_Y - 21.0, YAW_SERVO_FACE_Z + 38.5)),
            *_down_column(YAW_CHANNEL),
        ),
        lead=300.0,
    ),
    Run(
        "shoulder servo",
        "up beside the yaw bracket into the hood, down into the column to the servo driver",
        3,
        _anchored(
            # Out of the notch at the top of the bracket's window, up past the servo's top end,
            # and over the bracket beside the yaw horn.
            ("yaw", (_BRACKET_TAB_FACE_X - 1.0, 0.0, -10.0)),
            ("yaw", (_BRACKET_TAB_FACE_X - 2.0, 0.0, -5.0)),
            ("yaw", (_BRACKET_TAB_FACE_X - 2.0, 15.0, 0.0)),
            ("yaw", (_BRACKET_TAB_FACE_X, 17.0, 3.0)),
            *_UP_TO_HOOD,
            *_down_column(SHOULDER_CHANNEL),
        ),
        lead=300.0,
        moving=True,
    ),
    Run(
        "elbow servo",
        "upper arm clips, across the shoulder axis, into the hood, down the column",
        3,
        _anchored(
            ("upper_arm", (17.0, p.UPPER_ARM_L - 16.8, -4.0)),
            ("upper_arm", (17.0, p.UPPER_ARM_L - 16.8, -12.0)),
            *_UPPER_ARM_TO_HOOD,
            *_down_column(ELBOW_CHANNEL),
        ),
        lead=250.0,
        moving=True,
    ),
    Run(
        "gripper servo",
        "around the forearm's edge, forearm clips, across the elbow axis, then with the elbow servo's lead",
        3,
        _anchored(
            ("forearm", (-12.0, GRIPPER_Y - 16.8, 4.0)),
            ("forearm", (-12.0, GRIPPER_Y - 16.8, 18.0)),
            ("forearm", (7.0, 42.0, 18.0)),
            *_FOREARM_TO_HOOD,
            *_down_column(GRIPPER_CHANNEL),
        ),
        lead=250.0,
        moving=True,
    ),
    Run(
        "arm camera power",
        "5V and GND from the camera's header pins, with the gripper servo's lead, to the "
        "servo driver's spare channel (its V+ and GND)",
        2,
        _anchored(
            ("forearm", (15.0, CAM_FRONT_Y - 10.0, 11.4)),
            ("forearm", (7.0, 42.0, 12.0)),
            *_FOREARM_TO_HOOD,
            *_down_column(CAMERA_CHANNEL),
        ),
        moving=True,
    ),
    Run(
        "arm leads in the column",
        "the five arm leads together, from the hood floor's pass down in front of the plugs",
        14,
        _anchored(
            _COLUMN_TOP,
            _IN_FRONT_HIGH,
            ("tower", (_plug_end(0)[0] / 2, _BUNDLE_Y, _plug_end(4)[2] + 8.0)),
        ),
        check_only=True,
    ),
    # The ribbon, in two stacked layers: the servo driver bus (GND, SCL, SDA, VCC) and servo
    # power (V+ and GND, 22 AWG), then the stepper's five wires.
    Run(
        "tower ribbon",
        "servo driver bus (4) and servo power (2), and track stepper (5): down the column, through "
        "the carriage and the clamp tab, rolling loop along the channel, into the body at the port",
        11,
        _bundle_to_port,
        moving=True,
        diameter=p.RIBBON_THICKNESS,
    ),
    Run(
        "track stepper",
        "joins the ribbon in the carriage, through the port and the right wall hole to the ULN2003",
        5,
        _then(_stepper_to_port, _over(55.0, -45.0), *_wall_hole(-1, True), _ULN_SOCKET),
        lead=230.0,
        moving=True,
    ),
    # In the body.
    Run(
        "ribbon to Uno (I2C)",
        "from the port, over the front motors, to the Uno's SDA/SCL pins and its 5V and GND",
        4,
        _anchored(_PORT_BELOW, _OVER_FRONT_MOTORS, _over(20.0, -45.0), _UNO_I2C),
    ),
    Run(
        "ribbon to UBEC (servo power)",
        "V+ and GND (22 AWG): from the port, across the centre bay, through the left wall hole",
        2,
        _anchored(
            _PORT_BELOW, _OVER_FRONT_MOTORS, _over(10.0, 40.0), *_wall_hole(1, True), _UBEC_LEADS
        ),
        diameter=bundle_d(2, POWER_WIRE_D),
    ),
    Run(
        "UBEC to ULN2003",
        "5V and GND: left wall hole, across the centre bay, right wall hole",
        2,
        _anchored(_UBEC_LEADS, *_wall_hole(1, False), *_wall_hole(-1, True), _ULN_INPUTS),
    ),
    Run(
        "UBEC to nose camera",
        "5V and GND: left wall hole, over the front motors, to the camera's header pins",
        2,
        _anchored(
            _UBEC_LEADS, *_wall_hole(1, False), _over(50.0, 20.0), _over(95.0, 10.0), _NOSE_CAMERA
        ),
    ),
    Run(
        "Uno to ULN2003",
        "IN1-IN4 from A2, A3, D10, D11 (cut for the analog header, the further end), through the "
        "right wall hole",
        4,
        _anchored(_UNO_ANALOG, _over(-10.0, -20.0), *_wall_hole(-1, True), _ULN_INPUTS),
    ),
    Run(
        "Uno to front TB6612",
        "PWM, IN1, IN2 for both front motors, and the board's 5V and GND (STBY is jumpered to VCC)",
        8,
        _anchored(_UNO_DIGITAL, _over(10.0, -40.0), _TB_FRONT),
    ),
    Run(
        "Uno to rear TB6612",
        "PWM, IN1, IN2 for both rear motors, and the board's 5V and GND (STBY is jumpered to VCC)",
        8,
        _anchored(_UNO_DIGITAL, _over(10.0, -45.0), _TB_REAR),
    ),
    _motor("front left", p.MOTOR_X, 1),
    _motor("front right", p.MOTOR_X, -1),
    _motor("rear left", -p.MOTOR_X, 1),
    _motor("rear right", -p.MOTOR_X, -1),
)


def sweep() -> list[Pose]:
    """Poses spanning every joint's range, including its ends."""

    def steps(lo: float, hi: float, n: int) -> list[float]:
        return [lo + (hi - lo) * i / (n - 1) for i in range(n)]

    combos = itertools.product(
        steps(*CARRIAGE_RANGE, 5),
        steps(*YAW_RANGE, 7),
        steps(*SHOULDER_RANGE, 7),
        steps(*ELBOW_RANGE, 7),
        steps(*GRIP_RANGE, 3),
    )
    return [Pose(*c) for c in combos]


def length(points: list[Vector]) -> float:
    return sum((b - a).length for a, b in itertools.pairwise(points))


@dataclass(frozen=True)
class Sizing:
    run: Run
    shortest: float
    longest: float

    @property
    def cut(self) -> float:
        """Length to cut, rounded up to 10 mm."""
        return math.ceil((self.longest * SLACK + 2 * CONNECTOR_ALLOWANCE) / 10) * 10

    @property
    def extension(self) -> float | None:
        """How much the part's own lead falls short, if it does."""
        if self.run.lead is None:
            return None
        short = self.cut - self.run.lead
        return short if short > 0 else None


def sizing(poses: list[Pose] | None = None) -> list[Sizing]:
    poses = poses or sweep()
    results = []
    for run in RUNS:
        if run.check_only:
            continue
        lengths = [length(run.path(pose)) for pose in (poses if run.moving else poses[:1])]
        results.append(Sizing(run, min(lengths), max(lengths)))
    return results


def cable_shape(run: Run, pose: Pose, radius: float | None = None) -> Part:
    """The run's path as a chain of cylinders as thick as the cable, for renders and clearance checks."""
    radius = run.thickness / 2 if radius is None else radius
    points = run.path(pose)
    segments = []
    for a, b in itertools.pairwise(points):
        d = b - a
        if d.length < 1e-6:
            continue
        seg = cylinder(radius, (0, d.length))
        segments.append(_aim(seg, a, d))
    return Compound(children=segments)


def _aim(shape: Part, start: Vector, direction: Vector) -> Part:
    """Turn a +Z cylinder at the origin to start at `start` and point along `direction`."""
    from build123d import Location, Plane

    plane = Plane(origin=start, z_dir=direction.normalized())
    return Location(plane) * shape


def main() -> None:
    rows = sizing()
    width = max(len(s.run.name) for s in rows)
    print(f"{'run':<{width}}  wires  longest  cut   own lead")
    for s in rows:
        lead = "-" if s.run.lead is None else f"{s.run.lead:.0f}"
        note = f"  extend by {s.extension:.0f} mm" if s.extension else ""
        travel = f" (varies {s.shortest:.0f}-{s.longest:.0f})" if s.run.moving else ""
        print(
            f"{s.run.name:<{width}}  {s.run.wires:>5}  {s.longest:>7.0f}  {s.cut:>4.0f}  {lead:>8}{note}{travel}"
        )


if __name__ == "__main__":
    main()
