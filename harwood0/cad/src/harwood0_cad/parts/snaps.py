"""Snap fit holding the top plate onto the chassis.

Each snap is a thin arm rising from a chassis wall's inner face, up through a slot
in the top plate, with a barb on top that clicks over the plate's top face. Press
the plate down to fit it; push each barb in towards the body's interior to lift
it off. The arms print upright as part of the chassis.

`snap_arm` and `snap_slot` are built in a wall frame (origin on the wall's inner
face at the top plate's underside, +X pointing into the body, Z up) and placed by
`placed`, which turns them to face each wall.
"""

from build123d import Location, Part, Polyline, Pos, Rot, extrude, make_face

from harwood0_cad import params as p
from harwood0_cad.shapes import box

ARM_T = 2.0  # flexes along X
ARM_W = 6.0
ARM_GAP = 0.5  # between the arm and its wall
ARM_FREE_L = 18.0  # flexing length below the plate
ROOT_H = 4.0  # where the arm joins the wall, below its free length
BARB = 1.0  # how far the barb hooks over the plate
BARB_H = 2.5  # barb height above the plate's top face
SLOT_FLEX = 1.8  # room in the slot for the arm to flex inwards as the plate goes on


def snap_arm(plate_t: float) -> Part:
    """In the wall frame. Hangs from z=-ARM_FREE_L-ROOT_H to above the plate's top face."""
    x0, x1 = ARM_GAP, ARM_GAP + ARM_T
    hw = ARM_W / 2
    root = box((-0.1, x1), (-hw, hw), (-ARM_FREE_L - ROOT_H, -ARM_FREE_L))
    arm = box((x0, x1), (-hw, hw), (-ARM_FREE_L - 0.1, plate_t))
    # Barb: flat underside on the plate's top face, ramped top so the plate pushes it in.
    barb = Polyline(
        (x1, -hw, plate_t),
        (x0 - BARB, -hw, plate_t),
        (x0 - BARB, -hw, plate_t + 0.6),
        (x1, -hw, plate_t + BARB_H),
        close=True,
    )
    return root + arm + extrude(make_face(barb), amount=ARM_W, dir=(0, 1, 0))


def snap_slot(plate_t: float) -> Part:
    """The slot an arm passes through, in the wall frame; its outer edge is what the barb grips."""
    c = 0.3
    return box(
        (ARM_GAP - c, ARM_GAP + ARM_T + SLOT_FLEX),
        (-ARM_W / 2 - c, ARM_W / 2 + c),
        (-1, plate_t + 1),
    )


def placed(shape: Part, at: tuple[float, float], facing: float, z: float) -> Part:
    location: Location = Pos(at[0], at[1], z) * Rot(0, 0, facing)
    return location * shape


Snap = tuple[tuple[float, float], float]  # (x, y) on a wall's inner face, facing angle


def snap_arms(
    z: float, snaps: tuple[Snap, ...] = p.TOP_PLATE_SNAPS, plate_t: float = p.TOP_PLATE_T
) -> Part:
    """The snap arms for a plate of thickness `plate_t` whose underside sits at height `z`."""
    arms = None
    for at, facing in snaps:
        arm = placed(snap_arm(plate_t), at, facing, z)
        arms = arm if arms is None else arms + arm
    return arms


def snap_slots(
    snaps: tuple[Snap, ...] = p.TOP_PLATE_SNAPS, plate_t: float = p.TOP_PLATE_T, z: float = 0.0
) -> Part:
    """The matching slots through the plate, with its underside at height `z`."""
    slots = None
    for at, facing in snaps:
        slot = placed(snap_slot(plate_t), at, facing, z)
        slots = slot if slots is None else slots + slot
    return slots
