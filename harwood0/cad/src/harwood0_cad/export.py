"""Export printed parts to STL (for slicing) and STEP (for other CAD tools).

Only printed parts are exported, in their print orientation; hardware models
are never written out.
"""

import argparse
from pathlib import Path

from build123d import export_step, export_stl

from harwood0_cad.parts import PARTS, PRINT_ROTATIONS

DEFAULT_OUT = Path(__file__).resolve().parents[2] / "build"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("parts", nargs="*", help="part names to export (default: all)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="output directory")
    args = parser.parse_args()

    unknown = set(args.parts) - PARTS.keys()
    if unknown:
        parser.error(f"unknown parts: {', '.join(sorted(unknown))}; known: {', '.join(PARTS)}")

    args.out.mkdir(parents=True, exist_ok=True)
    for name in args.parts or PARTS:
        part = PARTS[name]()
        if name in PRINT_ROTATIONS:
            part = PRINT_ROTATIONS[name] * part
        export_stl(part, str(args.out / f"{name}.stl"))
        export_step(part, str(args.out / f"{name}.step"))
        print(f"exported {name} -> {args.out}")


if __name__ == "__main__":
    main()
