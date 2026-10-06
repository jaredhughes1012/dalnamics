"""Render parts, hardware, or the full assembly to PNG for visual checks.

Each image shows six orthographic views: front and rear isometric, front
(camera on +X looking back), right and left sides, and top. Printed parts are orange;
hardware is grey or its own colour.

    uv run harwood0-render                 # the full assembly
    uv run harwood0-render chassis mg90s   # individual parts or hardware
    uv run harwood0-render --all           # every part and hardware item
    uv run harwood0-render layout          # the robot plus the chassis and arm tower detached
    uv run harwood0-render print           # every printed part on the bed, in a grid
    uv run harwood0-render --only chassis,track,uno
    uv run harwood0-render assembly --cables --section x=-8.5   # cut-away through the tower
"""

import argparse
from pathlib import Path

import numpy as np
import pyvista as pv
from build123d import Shape

from harwood0_cad.assembly import Item, items_for
from harwood0_cad.hardware import HARDWARE
from harwood0_cad.parts import PARTS

DEFAULT_OUT = Path(__file__).resolve().parents[2] / "renders"
VIEWS = (
    ("isometric", (1, -1, 0.8), (0, 0, 1)),
    ("front (+X)", (1, 0, 0), (0, 0, 1)),
    ("top (+Z)", (0, 0, 1), (1, 0, 0)),
    ("rear isometric", (-1, 1, 0.8), (0, 0, 1)),
    ("right side (-Y)", (0, -1, 0), (0, 0, 1)),
    ("left side (+Y)", (0, 1, 0), (0, 0, 1)),
)


def to_mesh(shape: Shape, tolerance: float = 0.1) -> pv.PolyData:
    vertices, triangles = shape.tessellate(tolerance, angular_tolerance=0.2)
    points = np.array([(v.X, v.Y, v.Z) for v in vertices])
    faces = np.hstack([[3, *t] for t in triangles])
    # Tessellation duplicates vertices along face boundaries; merge them so edges are shared.
    return pv.PolyData(points, faces).clean()


def render(
    items: list[Item], path: Path, title: str, section: tuple[str, float] | None = None
) -> None:
    meshes = [(to_mesh(item.shape), item.color) for item in items]
    if section:
        # Cut everything away on the + side of the plane, to see inside.
        axis, value = section
        origin = {"x": (value, 0, 0), "y": (0, value, 0), "z": (0, 0, value)}[axis]
        meshes = [(m.clip(normal=axis, origin=origin), c) for m, c in meshes]
        meshes = [(m, c) for m, c in meshes if m.n_points]
    # Faces pointing the same way shade identically, so outline creases to keep features legible.
    edges = [
        mesh.extract_feature_edges(feature_angle=30, boundary_edges=False) for mesh, _ in meshes
    ]
    plotter = pv.Plotter(shape=(2, 3), off_screen=True, window_size=(2100, 1200))
    for index, (label, direction, up) in enumerate(VIEWS):
        plotter.subplot(index // 3, index % 3)
        for mesh, color in meshes:
            plotter.add_mesh(mesh, color=color, smooth_shading=False)
        for edge in (e for e in edges if e.n_points):
            plotter.add_mesh(edge, color="#222222", line_width=1)
        plotter.add_text(f"{title}: {label}", font_size=10)
        plotter.show_axes()
        plotter.enable_parallel_projection()
        plotter.camera_position = [np.array(direction) * 1000, (0, 0, 0), up]
        plotter.reset_camera()
    path.parent.mkdir(parents=True, exist_ok=True)
    plotter.screenshot(str(path))
    plotter.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("targets", nargs="*", help="'assembly', part names, or hardware names")
    parser.add_argument(
        "--all", action="store_true", help="render the assembly and every part and hardware item"
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--only", help="comma-separated assembly item names to include")
    parser.add_argument("--pose", default="neutral", help="named arm pose for the assembly")
    parser.add_argument("--cables", action="store_true", help="add the cable runs to the assembly")
    parser.add_argument("--section", help="cut away everything beyond a plane, e.g. x=-8.5 or y=0")
    args = parser.parse_args()

    known = {"assembly", "layout", "print", *PARTS, *HARDWARE}
    targets = (
        ["assembly", "layout", "print", *PARTS, *HARDWARE]
        if args.all
        else args.targets or ["assembly"]
    )
    unknown = set(targets) - known
    if unknown:
        parser.error(
            f"unknown targets: {', '.join(sorted(unknown))}; known: {', '.join(sorted(known))}"
        )

    for name in targets:
        only = set(args.only.split(",")) if args.only else None
        items = items_for(name, only=only, pose=args.pose, cables=args.cables)
        if name in ("assembly", "layout"):
            suffix = ("_detail" if args.only else "") + (
                "" if args.pose == "neutral" else f"_{args.pose}"
            )
            suffix += "_cables" if args.cables else ""
            suffix += f"_section_{args.section.replace('=', '')}" if args.section else ""
            path = args.out / f"{name}{suffix}.png"
        elif name == "print":
            path = args.out / "print.png"
        else:
            path = args.out / ("parts" if name in PARTS else "hardware") / f"{name}.png"
        section = None
        if args.section:
            axis, value = args.section.split("=")
            section = (axis.strip().lower(), float(value))
        render(items, path, name, section)
        print(f"rendered {name} -> {path}")


if __name__ == "__main__":
    main()
