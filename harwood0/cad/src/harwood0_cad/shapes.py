"""Small geometry helpers shared by hardware models and printed parts.

Most of this robot is boxes and cylinders placed by their extents, so these
helpers take (min, max) spans rather than centres and sizes.
"""

from build123d import Align, Box, Cylinder, Part, Pos, Rot

Span = tuple[float, float]

_MIN = (Align.MIN, Align.MIN, Align.MIN)
_BASE = (Align.CENTER, Align.CENTER, Align.MIN)


def box(x: Span, y: Span, z: Span) -> Part:
    """An axis-aligned box spanning the given ranges."""
    return Pos(x[0], y[0], z[0]) * Box(x[1] - x[0], y[1] - y[0], z[1] - z[0], align=_MIN)


def cylinder(radius: float, span: Span, axis: str = "z", at: tuple[float, float] = (0, 0)) -> Part:
    """A cylinder along `axis` covering `span`, centred at `at` in the other two axes.

    For axis "z", `at` is (x, y); for "y" it is (x, z); for "x" it is (y, z).
    """
    c = Cylinder(radius, span[1] - span[0], align=_BASE)
    match axis:
        case "z":
            return Pos(at[0], at[1], span[0]) * c
        case "y":
            return Pos(at[0], span[0], at[1]) * Rot(-90, 0, 0) * c
        case "x":
            return Pos(span[0], at[0], at[1]) * Rot(0, 90, 0) * c
    raise ValueError(f"unknown axis {axis!r}")


def d_shaft(diameter: float, flat: float, span: Span, flat_span: Span | None = None) -> Part:
    """A Z-axis shaft with a single D flat on +X; `flat` is the distance across the flat."""
    flat_span = flat_span or span
    r = diameter / 2
    return cylinder(r, span) - box((flat - r, r + 1), (-r - 1, r + 1), flat_span)


def double_d_shaft(diameter: float, flat: float, span: Span, flat_span: Span | None = None) -> Part:
    """A Z-axis shaft with two parallel flats normal to X; `flat` is the distance across them."""
    flat_span = flat_span or span
    r = diameter / 2
    cut = box((flat / 2, r + 1), (-r - 1, r + 1), flat_span)
    return cylinder(r, span) - cut - Rot(0, 0, 180) * cut
