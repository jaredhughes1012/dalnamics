"""Involute spur gears and matching racks (20 degree pressure angle)."""

import math

from build123d import Part, Polyline, extrude, make_face

FLANK_POINTS = 8
PRESSURE_ANGLE = 20.0


def _involute(angle: float) -> float:
    return math.tan(angle) - angle


def gear_profile(teeth: int, module: float, pressure_angle: float) -> list[tuple[float, float]]:
    """Outline of an involute spur gear, as a closed list of (x, y) points."""
    pa = math.radians(pressure_angle)
    r_pitch = module * teeth / 2
    r_base = r_pitch * math.cos(pa)
    r_tip = r_pitch + module
    r_root = r_pitch - 1.25 * module
    half_pitch_angle = math.pi / (2 * teeth) + _involute(pa)

    def half_angle(r: float) -> float:
        r = max(r, r_base)
        return half_pitch_angle - _involute(math.acos(r_base / r))

    radii = [r_root] + [
        max(r_base, r_root) + (r_tip - max(r_base, r_root)) * i / FLANK_POINTS
        for i in range(FLANK_POINTS + 1)
    ]
    points = []
    for tooth in range(teeth):
        centre = 2 * math.pi * tooth / teeth
        flank = [(r, centre - half_angle(r)) for r in radii]
        other = [(r, centre + half_angle(r)) for r in reversed(radii)]
        for r, a in flank + other:
            points.append((r * math.cos(a), r * math.sin(a)))
    return points


def rack_teeth(
    module: float, start: tuple[float, float, float], length: float, width: float, facing: int
) -> Part:
    """Rack teeth running along Z from `start`, standing on the plane y=start[1] and pointing
    along `facing` * Y, `width` thick along +X from start[0]. Pitch line is 1.25 module out."""
    pitch = math.pi * module
    tan = math.tan(math.radians(PRESSURE_ANGLE))
    root_half = pitch / 4 + 1.25 * module * tan
    tip_half = pitch / 4 - module * tan
    x0, y0, z0 = start
    root, tip = y0, y0 + facing * 2.25 * module
    teeth = None
    for i in range(int(length / pitch)):
        cz = z0 + pitch * (i + 0.5)
        profile = Polyline(
            (x0, root - facing * 0.01, cz - root_half),
            (x0, root - facing * 0.01, cz + root_half),
            (x0, tip, cz + tip_half),
            (x0, tip, cz - tip_half),
            close=True,
        )
        tooth = extrude(make_face(profile), amount=width, dir=(1, 0, 0))
        teeth = tooth if teeth is None else teeth + tooth
    return teeth
