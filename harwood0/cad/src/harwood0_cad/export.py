"""Export printed parts to STL (for slicing) and STEP (for other CAD tools).

Only printed parts are exported, in their print orientation and sitting on the
bed (Z=0); hardware models are never written out. Files are sorted by format, then
by which part of the robot they belong to:

    build/stl/body/chassis.stl        build/step/body/chassis.step
    build/stl/tower/hood.stl          build/step/tower/hood.step
    build/stl/arm/upper_arm.stl       ...
    build/stl/test/tolerance_coupon.stl

    uv run harwood0-cad                  # every part
    uv run harwood0-cad chassis hood     # just these
"""

import argparse
from pathlib import Path

from build123d import export_step, export_stl

from harwood0_cad.parts import PART_GROUP, PARTS
from harwood0_cad.printing import print_part

DEFAULT_OUT = Path(__file__).resolve().parents[2] / "build"
FORMATS = {"stl": export_stl, "step": export_step}


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("parts", nargs="*", help="part names to export (default: all)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="output directory")
    args = parser.parse_args()

    unknown = set(args.parts) - PARTS.keys()
    if unknown:
        parser.error(f"unknown parts: {', '.join(sorted(unknown))}; known: {', '.join(PARTS)}")

    for name in args.parts or PARTS:
        part = print_part(name)
        for ext, export in FORMATS.items():
            path = args.out / ext / PART_GROUP[name] / f"{name}.{ext}"
            path.parent.mkdir(parents=True, exist_ok=True)
            export(part, str(path))
            # Remove the copy from before exports were sorted into folders, if there is one.
            (args.out / f"{name}.{ext}").unlink(missing_ok=True)
        print(f"exported {name} -> {args.out / '{stl,step}' / PART_GROUP[name]}")


if __name__ == "__main__":
    main()
