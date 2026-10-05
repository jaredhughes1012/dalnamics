"""Part registry: every printable part is registered here by name."""

from collections.abc import Callable

from build123d import Location, Part, Rot

from harwood0_cad.parts.chassis import chassis
from harwood0_cad.parts.deck import deck
from harwood0_cad.parts.pan_head import pan_head
from harwood0_cad.parts.tilt_bracket import tilt_bracket
from harwood0_cad.parts.tolerance_coupon import tolerance_coupon

PARTS: dict[str, Callable[[], Part]] = {
    "chassis": chassis,
    "deck": deck,
    "pan_head": pan_head,
    "tilt_bracket": tilt_bracket,
    "tolerance_coupon": tolerance_coupon,
}

# Parts modelled in their assembled orientation that print better another way up.
# Export applies these; anything not listed prints as modelled.
PRINT_ROTATIONS: dict[str, Location] = {
    "tilt_bracket": Rot(-90, 0, 0),  # back face down on the bed
}
