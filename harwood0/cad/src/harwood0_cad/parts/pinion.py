"""Pinion: an involute spur gear on the track stepper's shaft, driving the carriage along the rack.

Presses onto the 28BYJ-48's double-D shaft. Printed flat.

Local frame: gear axis along Z, faces at Z=0 and Z=PINION_T.
"""

from build123d import Part, Polyline, Rot, extrude, make_face

from harwood0_cad import params as p
from harwood0_cad.arm_geometry import PINION_MODULE, PINION_TEETH
from harwood0_cad.gears import gear_profile
from harwood0_cad.hardware.motors import BYJ_SHAFT_D, BYJ_SHAFT_FLAT
from harwood0_cad.shapes import double_d_shaft
from harwood0_cad.track_geometry import RACK_PRESSURE_ANGLE

PINION_T = 6.0


def pinion() -> Part:
    outline = gear_profile(PINION_TEETH, PINION_MODULE, RACK_PRESSURE_ANGLE)
    gear = extrude(make_face(Polyline(*outline, close=True)), amount=PINION_T)
    bore = double_d_shaft(BYJ_SHAFT_D + 0.3, BYJ_SHAFT_FLAT + p.FIT_CLEARANCE, (-1, PINION_T + 1))
    # Flats normal to Y here, so they line up with the stepper's shaft once both are placed.
    return gear - Rot(0, 0, 90) * bore
