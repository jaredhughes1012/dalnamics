"""Printed parts as they go on the bed: turned to their print orientation, sitting on Z=0.

`print_layout` lays out one of every part the robot needs (two where it needs two) in a
grid, for checking print orientations and the full print list at a glance.
"""

from build123d import Part, Pos

from harwood0_cad.parts import PARTS, PRINT_ROTATIONS

# How many of each part one robot needs; anything not listed is printed once. Test prints
# that are not part of the robot are 0, and are left out of the layout.
PRINT_QUANTITIES: dict[str, int] = {"track_lip": 2, "chassis_fit_section": 0}

GRID_GAP = 20.0  # between parts, in both directions
GRID_ROW_WIDTH = 700.0  # start a new row once a row would grow past this


def print_part(name: str) -> Part:
    """The part in its print orientation, centred over the origin with its base on Z=0."""
    part = PARTS[name]()
    if name in PRINT_ROTATIONS:
        part = PRINT_ROTATIONS[name] * part
    box = part.bounding_box()
    return Pos(-box.center().X, -box.center().Y, -box.min.Z) * part


def print_layout() -> list[tuple[str, Part]]:
    """Every part to print, in print orientation, packed into rows: largest first, rows
    running along +X and stacking towards -Y."""
    parts = []
    for name in PARTS:
        shape = print_part(name)
        count = PRINT_QUANTITIES.get(name, 1)
        for i in range(count):
            parts.append((name if count == 1 else f"{name} {i + 1}", shape))
    parts.sort(key=lambda item: -item[1].bounding_box().size.Y)

    placed = []
    x = y = row_depth = 0.0
    for label, shape in parts:
        size = shape.bounding_box().size
        if x > 0 and x + size.X > GRID_ROW_WIDTH:
            x, y, row_depth = 0.0, y - row_depth - GRID_GAP, 0.0
        placed.append((label, Pos(x + size.X / 2, y - size.Y / 2, 0) * shape))
        x += size.X + GRID_GAP
        row_depth = max(row_depth, size.Y)
    return placed
