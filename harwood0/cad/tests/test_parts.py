import pytest

from harwood0_cad import params
from harwood0_cad.parts import PART_GROUPS, PARTS, top_plate
from harwood0_cad.printing import print_part


@pytest.fixture(params=sorted(PARTS), ids=str)
def part(request):
    """The part as it sits on the bed."""
    return print_part(request.param)


def test_part_is_valid_solid(part):
    assert part.is_valid
    assert part.volume > 0


def test_part_fits_build_volume(part):
    size = part.bounding_box().size
    for axis, (actual, limit) in zip("XYZ", zip(size, params.BUILD_VOLUME)):
        assert actual <= limit, f"{axis} extent {actual:.1f} mm exceeds build volume {limit} mm"


def test_top_plate_lies_flat_on_its_underside():
    """Nothing hangs below the plate's underside, which it prints on."""
    assert top_plate().bounding_box().min.Z == pytest.approx(0.0)


def test_every_part_has_one_export_group():
    grouped = [name for names in PART_GROUPS.values() for name in names]
    assert sorted(grouped) == sorted(PARTS)
