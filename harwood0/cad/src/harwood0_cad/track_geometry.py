"""Track geometry, shared by the top plate (which carries the track) and the arm's carriage.

Heights are above the top plate's underside; X and Y are global.
"""

from harwood0_cad import params as p

# Track strip and slot.
TRACK_T = 10.0
SLOT_Y = sum(p.TRACK_Y) / 2  # slot centreline
SLOT_TOP_W = 14.0
SLOT_BOTTOM_W = 22.0
SLOT_DEPTH = 7.0
SLOT_FLOOR_Z = TRACK_T - SLOT_DEPTH
SLOT_END_WALL = 8.0  # solid strip left at each end of the slot

# Entry pocket: a straight-walled section at the slot's rear end, long enough to lower the
# whole carriage in. Two lip strips then screw into it and rebuild the dovetail, so the
# carriage can run the full slot.
ENTRY_L = p.CARRIAGE_L + 2.0
# Wide enough that the lip strips have room round their screws' clearance holes and
# counterbores at M3.
POCKET_HALF_W = 17.5
# Lip strip screws, either side of the slot centreline: as far out as the top plate's insert
# bosses allow, hanging beside the motor wall, for plastic between the hole and the
# dovetail's slope at the strip's foot.
LIP_SCREW_Y = 13.3
LIP_SCREW_INSET = 8.0  # from each end of the pocket

# Rack: 20 degree pressure angle, teeth standing on the slot floor along its centreline.
RACK_MODULE = 1.5
RACK_PRESSURE_ANGLE = 20.0
RACK_FACE_W = 6.0
RACK_PITCH_Z = SLOT_FLOOR_Z + 1.25 * RACK_MODULE  # pitch line height above the plate underside

# Usable slot, front and rear, in the global X frame.
SLOT_X = (p.TRACK_X[0] + SLOT_END_WALL, p.TRACK_X[1] - SLOT_END_WALL)
POCKET_X = (SLOT_X[0], SLOT_X[0] + ENTRY_L)
