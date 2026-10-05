"""Static tipping check: estimated mass, centre of mass, and how far inside the wheels it sits.

The robot stands on its four wheel contact patches, so it tips once its centre of
mass passes outside the rectangle they form. The margin is the distance from the
centre of mass (projected onto the ground) to the nearest edge of that rectangle.
It is a static figure: acceleration, braking, and payloads all eat into it.

    uv run harwood0-stability
"""

from build123d import CenterOf, Vector

from harwood0_cad import params as p
from harwood0_cad.assembly import Item, robot

PLA_DENSITY = 1.24e-3  # g/mm^3
PRINT_FILL = (
    0.6  # fraction of a printed part's volume that is plastic, with typical walls and infill
)
MIN_TIP_MARGIN = 30.0  # mm, required in every pose


def item_mass(item: Item) -> float:
    return item.shape.volume * PLA_DENSITY * PRINT_FILL if item.printed else item.mass


def center_of_mass(items: list[Item]) -> tuple[float, Vector]:
    total = 0.0
    moment = Vector(0, 0, 0)
    for item in items:
        mass = item_mass(item)
        total += mass
        moment += item.shape.center(CenterOf.MASS) * mass
    return total, moment / total


def support_rectangle() -> tuple[tuple[float, float], tuple[float, float]]:
    """The X and Y spans of the wheel contact patches."""
    return (-p.MOTOR_X, p.MOTOR_X), (-p.WHEEL_Y, p.WHEEL_Y)


def tipping_margin(items: list[Item]) -> float:
    """Distance from the centre of mass to the nearest support edge; negative means it tips."""
    _, com = center_of_mass(items)
    (x0, x1), (y0, y1) = support_rectangle()
    return min(com.X - x0, x1 - com.X, com.Y - y0, y1 - com.Y)


def report(name: str, items: list[Item]) -> str:
    mass, com = center_of_mass(items)
    margin = tipping_margin(items)
    return f"{name}: {mass:.0f} g, centre of mass ({com.X:.0f}, {com.Y:.0f}, {com.Z:.0f}) mm, tip margin {margin:.0f} mm"


def main() -> None:
    print(report("robot", robot()))


if __name__ == "__main__":
    main()
