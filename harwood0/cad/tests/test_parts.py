import pytest

from harwood0_cad import params
from harwood0_cad.parts import PARTS
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
