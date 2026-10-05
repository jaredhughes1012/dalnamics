"""Fit checks: nothing in the assembly overlaps a printed part.

Parts touching face-to-face is fine (zero overlap volume); anything more means a
part or a placement is wrong. The camera head is checked across its range.
"""

import itertools

import pytest

from harwood0_cad.assembly import assembly
from harwood0_cad.hardware import HARDWARE

# Overlap volume (mm^3) below which a contact counts as face-to-face.
TOLERANCE = 0.5

POSES = [(0, 0), (0, 45), (0, -45), (90, 30), (-120, -30), (180, 0)]


def _bbox_overlap(a, b) -> bool:
    ba, bb = a.bounding_box(), b.bounding_box()
    return all(
        lo_a < hi_b and lo_b < hi_a
        for lo_a, hi_a, lo_b, hi_b in zip(ba.min, ba.max, bb.min, bb.max)
    )


@pytest.mark.parametrize("pan,tilt", POSES, ids=[f"pan{p}_tilt{t}" for p, t in POSES])
def test_no_interference_with_printed_parts(pan, tilt):
    items = assembly(pan=pan, tilt=tilt)
    clashes = []
    for a, b in itertools.combinations(items, 2):
        if not (a.printed or b.printed) or not _bbox_overlap(a.shape, b.shape):
            continue
        volume = (a.shape & b.shape).volume
        if volume > TOLERANCE:
            clashes.append(f"{a.name} x {b.name}: {volume:.1f} mm^3")
    assert not clashes, "\n".join(clashes)


@pytest.mark.parametrize("name", sorted(HARDWARE))
def test_hardware_builds(name):
    shape = HARDWARE[name]()
    assert shape.volume > 0
