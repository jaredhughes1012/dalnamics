# harwood0 bill of materials

Consolidated parts list for the **physical** harwood0 — the rover platform, the
3-joint arm, and the parts shared between them. Derived from the actuators/sensors
table, pin map, and power rails in [`electronics/README.md`](electronics/README.md)
and the purchased-part dimensions in [`cad/params.py`](cad/params.py). Printed
structural parts are in the [hardware README's print table](README.md#printing);
this list covers everything that is **bought**.

This is the canonical, build-from-scratch list. Build-specific notes (parts already
on hand, substitutions, what's been ordered) belong in `BOM_local.md`, not here.

Split convention: a part lives under **Arm** or **Rover** if it physically belongs
to / serves only that subsystem, and under **Shared** if it serves both (the Uno
motion controller drives both subsystems; the servo power rail feeds servos on
both).

---

## Rover

| # | Part | Qty | Spec | Notes |
|---|---|---|---|---|
| R1 | DC gearmotor (rear drive) | 1 | GA25YN370, **12 V / 200 RPM** — Ø25 can + gearhead, Ø4 D-shaft, 2× M3 gearbox-face mount holes (`GEARMOTOR_*`); 3.5 W, ~0.06 A no-load, 96 g | ~34 cm/s at the wheel through the 2:1 belt. Sits in an elevated bed well OVER the axle, face-bolted to the well bulkhead (`bed.py`); drives the rear live axle through a VERTICAL GT2 belt (`rear_drive.py`). Motor rail runs at 12 V (S4) — keep servos on the separate 5–6 V UBEC |
| R2 | Motor driver | 1 | TB6612FNG (preferred) or DRV8833 | PWMA=D5, AIN1/2=D7/D8, STBY=D13 |
| R3 | Steering servo | 1 | MG90S (metal gear) | Center-pivot linkage on `front_axle.py`; D9 |
| R4 | Wheels | 4 | 65 mm dia × 26 mm wide (`WHEEL_DIAMETER`/`WHEEL_WIDTH`) | Purchased — not printed |
| R5 | Axle rod | — | 6 mm dia steel rod (`AXLE_ROD_DIA`) | Cut to length for front + rear axles |
| R6 | Ball bearings | 8 | F696ZZ flanged, 6×13×5 mm (`BEARING_OD`/`BEARING_WIDTH`/`BEARING_FLANGE_OD`) | 2 rear-drive (live axle) + 2 per front knuckle hub (live stub) + 2 in the yaw housing (yaw shaft); all press into printed seats (`components.bearing_pocket`) |
| R6b | GT2 pulleys | 2 | `MOTOR_PULLEY_T` = 16T (bore Ø`GEARMOTOR_SHAFT_DIA`) + `AXLE_PULLEY_T` = 32T (bore Ø`AXLE_ROD_DIA`), 6 mm | Rear-drive reduction ≈ 2:1; set screws onto motor shaft + axle |
| R6c | GT2 belt | 1 | 6 mm closed loop, ≈130 mm (`BELT_LENGTH` ≈ 129 mm → nearest standard) | Couples motor pulley → axle pulley (runs vertically); tension set by choosing `MOTOR_DZ` to a stock loop |
| R6d | Motor mount screws | 2 | M3 into the gearmotor's gearbox-face tapped holes | Face-bolt the gearmotor to the bed-well bulkhead (`bed.py`); fit the motor before sliding the pulley on |
| R7 | Activation-code display | 1 | 1.3" SH1106 OLED, I2C | Mounts in the bed rear wall (`chassis.py`); SDA/SCL |
| R8 | Chassis seam screws | 4 | M3 (`SEAM_BOLT_D` = 3.4 mm clearance) | Join the 3 bed pieces — one screw per side-wall boss at each of the 2 seams |
| R9 | Wheel-well screws | 8 | M3 self-tap (`WELL_BOLT_D` = 3.4) | 2 per well × 4 wells, inset in the rounded well top, down into the side-wall lugs |
| R10 | Display module screws | 4 | M2.5 self-tap (`DISPLAY_BOSS_PILOT_D` = 2.1) | OLED module → bed rear-wall bosses |

## Arm

| # | Part | Qty | Spec | Notes |
|---|---|---|---|---|
| A1 | Base yaw stepper | 1 | 28BYJ-48 (5 V) | Turns the yaw shaft (`centered_base.py`); the arm's weight + tipping moment ride two bearings, NOT the stepper shaft, so it only fights bearing friction — but confirm it overcomes that + yaw inertia |
| A1b | Yaw shaft | 1 | 6 mm dia steel rod (`YAW_SHAFT_DIA`) | Spins in two F696ZZ in the housing; turntable clamps on top |
| A1c | Yaw thrust collar | 1 | 6 mm bore clamp collar | On the shaft, rests on the upper bearing's inner race — takes the arm's axial weight |
| A2 | Stepper driver board | 1 | ULN2003 | IN1–IN4 = D2/D3/D4/D12 |
| A3 | Shoulder servo | 1 | DS3218 (20 kg·cm) or MG996R (~11 kg·cm) — see [Servo sizing](#servo-sizing) | D10; lifts the whole forearm + head |
| A4 | Elbow servo | 1 | MG996R (~11 kg·cm) — see [Servo sizing](#servo-sizing) | D11; lifts head + payload |
| A5 | Gripper finger servos | 3 | MG90S (metal gear) | One per finger; D6, A3, A4 |
| A6 | Fingertip force sensors | 3 | FSR (force-sensing resistor), e.g. FSR-402/RP-C | One per fingertip pad; A0–A2 |
| A7 | FSR pulldown resistors | 3 | 10 kΩ | Divider to GND, one per FSR |
| A8 | Head camera | 1 | ESP32-CAM (AI-Thinker, OV2640) | On the camera boom (`arm_head.py`); own WiFi stream |
| A9 | Hinge pins | ~1 | 4 mm dia rod/dowel (`JOINT_PIN_D`) | Knuckle/clevis pivots (head tilt); the pitch joints are servo-driven drums, not pinned |
| A10 | Finger linkage pins | ~12 | 4 mm dia (`FINGER_PIN_D`) | Per finger: fixed pivot (B) + over-center stop + crank pin (C) + coupler pin (D) |
| A11 | Camera-hinge pin | 1 | small dowel | Adjustable camera tilt (`HINGE_DIA` = 12) |
| A12 | Servo mount + horn screws | ~30 | M2–M3 (`HORN_BOLT_D` = 2.4 horn→yoke, `CAP_SCREW_D` = 3.4 cap→drum, `SG90_BOLT_D` = 2.2 finger tabs) | Cap screws clamp each joint servo in its drum; horn screws bolt the adapter yoke to the servo horn; finger servos self-tap into their bracket |
| A13 | Fingertip rubber pads | 3 | adhesive rubber/silicone, ~9 mm | Over the FSR in the tip recess (`FSR_PAD`) |
| A14 | Arm-base mount screws | 4 | M3 (`ARM_MOUNT_BOLT_D` = 3.4) | Base ring → chassis boss |
| A15 | Shoulder counterspring | 1 | elastic cord — latex tubing or bungee, ~16 mm free length between posts, ~870 N/m (see [Counterspring](#shoulder-counterspring)) | Cancels ~85% of the shoulder's standing 6.0 kg·cm; hooks the shoulder cap to the yoke's tail post (`arm/counterbalance.py`). Tune by shortening it or moving one anchor hole |
| A16 | Counterspring posts | 2 | M3 × 8 + washer (`CB_PILOT_D` = 2.6 self-tap) | One in the cap's anchor pad, one in the yoke tail's end face; the cord's loop is trapped under each head |

## Shared

| # | Part | Qty | Spec | Notes |
|---|---|---|---|---|
| S1 | Motion controller | 1 | Arduino Uno R4 WiFi | Enclosed rear hardware bay; drives **both** rover + arm, serves the HTTP motion API |
| S2 | Servo power supply (UBEC) | 1 | 5–6 V, ≥ 5 A | Feeds **all 6 servos** — *not* the Uno 5 V pin; see [Power](#power-budget) |
| S3 | ESP32-CAM power | 1 | clean 5 V ≥ 2 A | Brown-outs easily; thin 2-wire lead up the arm |
| S4 | Main battery | 1 | 7–12 V pack (2S/3S LiPo or NiMH) | Uno VIN + motor VM; size to runtime |
| S5 | Wiring / connectors | — | Dupont jumpers, JST, 22 AWG | **Tie all grounds together** (Uno, UBEC, motor, ESP32-CAM) |
| S6 | Power switch + fuse | 1 ea | inline, sized to battery | Main cutoff |
| S7 | Print filament | — | PLA / PETG | All printed parts (see README print table) |

---

## Servo sizing

The six servos split into two torque classes.

**Low-torque (micro servos fine):** steering (R3) and the three gripper fingers
(A5). Use **MG90S** (metal gear) rather than plastic-gear SG90 — the gripper closes
against the FSRs under load and SG90 horns/gears strip over repeated grip cycles.

**High-torque (micro servos inadequate):** shoulder (A3) and elbow (A4). A rough
static hold with the arm extended horizontal (forearm + elbow servo + head ≈ 90 g
head + ~100 g payload at effective reach ~0.15 m) needs on the order of:

- **Shoulder ≈ 4–5 kg·cm static**, so ~10–13 kg·cm with dynamic + safety margin.
- **Elbow ≈ 2.5 kg·cm static**, so ~6–7 kg·cm with margin.

SG90 (~1.8 kg·cm) and MG90S (~2.2 kg·cm) can hold neither joint under load.

| Joint | Servo | Torque (6 V) | Why |
|---|---|---|---|
| Shoulder (A3) | DS3218 (20 kg·cm) or MG996R (~11 kg·cm) | 11–20 kg·cm | Highest load; DS3218 gives comfortable margin |
| Elbow (A4) | MG996R (~11 kg·cm) | ~11 kg·cm | Comfortable margin over the ~6–7 kg·cm need |
| Steering (R3), Gripper (A5 ×3) | MG90S | ~2.2 kg·cm | Low load; metal gear for durability |

These figures assume a **~100 g payload at the full ~210 mm reach**. A much lighter
payload and shorter reaches relax the shoulder/elbow requirement — recompute before
downsizing.

Since measured off the CAD (322 g distal to the shoulder at x̄ = 186 mm), the shoulder's
**unloaded** static hold is **6.0 kg·cm** with the arm extended — ~30% of a DS3218's stall
carried continuously, before any payload. Keep the DS3218 rather than the MG996R here.

### Shoulder counterspring

An elastic cord (A15) between the shoulder cap and the yoke's tail post cancels most of that
standing moment at **every** joint angle, not just one — both ends sit on the same ray through
the pitch axis at the pose where gravity exerts no torque, so the spring's torque and
gravity's are the same function of angle. It leaves ~0.8 kg·cm on the servo. That matters for
more than heating: the standing load is what makes the drive backlash visible, since the horn
and the printed yoke deflect in proportion to it.

Sizing, the fit against a real cord's free length, and the swept clearance check all live in
`arm/counterbalance.py` — run `uv run python -m arm.counterbalance` from `hardware/cad/` for
the current spec. It assists the **shoulder only**: the elbow's gravity torque depends on the
shoulder angle too, so a spring fixed to the elbow's own drum would only be right with the arm
straight up (and the elbow holds just 1.7 kg·cm).

**CAD impact:** the shoulder/elbow joints size their servo pockets by subtracting the
faithful `components.ds3218()` solid (driven by the `DS_3218_*` numbers in
`measurements.py`), so the drum is already cut for a standard-size servo. Switching to a
different standard-size servo (e.g. MG996R) is a `measurements.py` edit plus re-export of
`centered_joint.py` (the drum/cap) — no geometry edits. The gripper pockets subtract
`components.sg90()` and stay as-is for MG90S.

## Power budget

The actuator count is **6 servos** (1 steering + shoulder + elbow + 3 fingers).
With the shoulder/elbow at the MG996R/DS3218 class their stall current dominates:

- 4× MG90S (~0.7 A stall each) + 2× MG996R/DS3218 (~2.5 A stall each) ≈ momentary
  worst case well over 5 A. Real draw is far lower (not all stall at once), but
  size the UBEC (**S2**) at **≥ 5 A** and keep it off the Uno's 5 V rail.
- ESP32-CAM gets its **own** clean 5 V ≥ 2 A rail (**S3**) — don't share it with
  the servos.
- DC motor (**R1**) runs off battery → TB6612 `VM`; logic VCC = 5 V; common GND.
- Stepper (**A1**) runs 5 V into the ULN2003 board.

Tie **all** grounds together (battery, UBEC, ESP32-CAM, Uno).

> Note: `electronics/README.md`'s power-rails section still says "Servos (4×)" —
> that predates the 3-finger gripper. The real count is 6.
