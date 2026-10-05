"""Plan-view outline shared by the chassis, top plate, and work table."""

from build123d import Axis, Part, fillet

from harwood0_cad import params as p
from harwood0_cad.shapes import Span, box

MIN_CORNER_R = 1.0


def body_plan(inset: float, z: Span) -> Part:
    """The body outline shrunk by `inset` on every side, extruded over `z`.

    The nose corners are rounded with NOSE_R and the tail corners with TAIL_R, both
    reduced by `inset` so that offsets stay concentric (down to MIN_CORNER_R).
    """
    x0, x1 = -p.CHASSIS_L / 2 + inset, p.CHASSIS_L / 2 - inset
    hw = p.CHASSIS_W / 2 - inset
    plan = box((x0, x1), (-hw, hw), z)
    nose = plan.edges().filter_by(Axis.Z).filter_by_position(Axis.X, 0, x1 + 1)
    plan = fillet(nose, max(p.NOSE_R - inset, MIN_CORNER_R))
    tail = plan.edges().filter_by(Axis.Z).filter_by_position(Axis.X, x0 - 1, 0)
    return fillet(tail, max(p.TAIL_R - inset, MIN_CORNER_R))
