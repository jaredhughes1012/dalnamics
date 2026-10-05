"""Models of purchased hardware.

These are for fit checks and renders only: they are never exported as print
files. Each model is built in its own local frame, documented on its function,
and the dimensions are module constants so printed parts can be sized from them.
Dimensions are typical datasheet values; confirm with calipers against the real
part and update the constant if they differ.
"""

from collections.abc import Callable

from build123d import Part

from harwood0_cad.hardware.battery import lipo_3s
from harwood0_cad.hardware.boards import (
    dupont_housing,
    esp32_cam,
    pca9685,
    tb6612,
    ubec,
    uln2003,
    uno_r4_wifi,
)
from harwood0_cad.hardware.motors import (
    ds3218,
    ga25_motor,
    mg90s,
    mg90s_horn,
    mg996r,
    standard_horn,
    stepper_28byj48,
)
from harwood0_cad.hardware.wheels import mecanum_wheel

HARDWARE: dict[str, Callable[[], Part]] = {
    "ga25_motor": ga25_motor,
    "mecanum_wheel": mecanum_wheel,
    "stepper_28byj48": stepper_28byj48,
    "mg90s": mg90s,
    "mg90s_horn": mg90s_horn,
    "ds3218": ds3218,
    "mg996r": mg996r,
    "standard_horn": standard_horn,
    "uno_r4_wifi": uno_r4_wifi,
    "tb6612": tb6612,
    "pca9685": pca9685,
    "dupont_housing": dupont_housing,
    "uln2003": uln2003,
    "esp32_cam": esp32_cam,
    "ubec": ubec,
    "lipo_3s": lipo_3s,
}
