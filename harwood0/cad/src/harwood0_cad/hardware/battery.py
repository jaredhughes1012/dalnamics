"""Main battery pack."""

from build123d import Axis, Part, fillet

from harwood0_cad.shapes import box, cylinder

# 3S 11.1 V ~2200 mAh LiPo (BOM S4).
LIPO_L = 105.0
LIPO_W = 35.0
LIPO_H = 25.0


def lipo_3s() -> Part:
    """Origin at the bottom centre; long axis along X, leads out of the -X end."""
    pack = box((-LIPO_L / 2, LIPO_L / 2), (-LIPO_W / 2, LIPO_W / 2), (0, LIPO_H))
    pack = fillet(pack.edges().filter_by(Axis.X), radius=3)
    for y in (-5, 5):
        pack += cylinder(1.5, (-LIPO_L / 2 - 12, -LIPO_L / 2), axis="x", at=(y, LIPO_H / 2))
    return pack
