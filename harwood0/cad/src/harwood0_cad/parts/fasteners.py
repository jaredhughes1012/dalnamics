"""Holes for the structural screws: heat-set insert holes, and hex pockets for nuts.

Each takes the face the hole opens on and the direction it runs into the part (+1 or -1
along `axis`), with `at` as for `shapes.cylinder`.
"""

import math

from build123d import Part, Pos, RegularPolygon, Rot, extrude

from harwood0_cad import params as p
from harwood0_cad.shapes import cylinder


def _span(face: float, into: int, depth: float) -> tuple[float, float]:
    """From just outside `face` to `depth` into the part."""
    return tuple(sorted((face - into, face + into * depth)))


def insert_hole(face: float, into: int, at: tuple[float, float], axis: str = "z") -> Part:
    """A hole for a heat-set insert, pressed in from `face`."""
    return cylinder(p.INSERT_HOLE_D / 2, _span(face, into, p.INSERT_DEPTH), axis=axis, at=at)


def nut_pocket(face: float, into: int, at: tuple[float, float], angle: float = 0.0) -> Part:
    """A hex pocket for a nut, opening upwards or downwards on a Z face; flats face +-X
    when `angle` is 0."""
    af = p.NUT_AF + 2 * p.NUT_CLEARANCE
    hexagon = Rot(0, 0, angle + 30) * RegularPolygon(af / 2, 6, major_radius=False)
    z = _span(face, into, p.NUT_T + p.NUT_CLEARANCE)
    return Pos(at[0], at[1], z[0]) * extrude(hexagon, amount=z[1] - z[0])


def nut_corner_r() -> float:
    """How far a nut pocket reaches from its centre, at the corners."""
    return (p.NUT_AF / 2 + p.NUT_CLEARANCE) / math.cos(math.radians(30))
