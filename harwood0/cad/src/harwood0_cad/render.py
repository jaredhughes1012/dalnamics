"""Render parts, hardware, or the full assembly to PNG for visual checks.

Each image shows four orthographic views: isometric, front (camera on +X
looking back), right side (camera on -Y), and top. Printed parts are orange;
hardware is grey or its own colour.

    uv run harwood0-render                 # the full assembly
    uv run harwood0-render chassis mg90s   # individual parts or hardware
    uv run harwood0-render --all           # every part and hardware item
    uv run harwood0-render --only pan_head,tilt_bracket,camera --pan 90 --tilt 30
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
    ("right side (-Y)", (0, -1, 0), (0, 0, 1)),
    ("top (+Z)", (0, 0, 1), (1, 0, 0)),
)


def to_mesh(shape: Shape, tolerance: float = 0.1) -> pv.PolyData:
    vertices, triangles = shape.tessellate(tolerance, angular_tolerance=0.2)
    points = np.array([(v.X, v.Y, v.Z) for v in vertices])
    faces = np.hstack([[3, *t] for t in triangles])
    # Tessellation duplicates vertices along face boundaries; merge them so edges are shared.
    return pv.PolyData(points, faces).clean()


def render(items: list[Item], path: Path, title: str) -> None:
    meshes = [(to_mesh(item.shape), item.color) for item in items]
    # Faces pointing the same way shade identically, so outline creases to keep features legible.
    edges = [
        mesh.extract_feature_edges(feature_angle=30, boundary_edges=False) for mesh, _ in meshes
    ]
    plotter = pv.Plotter(shape=(2, 2), off_screen=True, window_size=(1600, 1200))
    for index, (label, direction, up) in enumerate(VIEWS):
        plotter.subplot(index // 2, index % 2)
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
    parser.add_argument("--pan", type=float, default=0.0, help="camera pan angle for the assembly")
    parser.add_argument(
        "--tilt", type=float, default=0.0, help="camera tilt angle for the assembly"
    )
    args = parser.parse_args()

    known = {"assembly", *PARTS, *HARDWARE}
    targets = ["assembly", *PARTS, *HARDWARE] if args.all else args.targets or ["assembly"]
    unknown = set(targets) - known
    if unknown:
        parser.error(
            f"unknown targets: {', '.join(sorted(unknown))}; known: {', '.join(sorted(known))}"
        )

    for name in targets:
        only = set(args.only.split(",")) if args.only else None
        items = items_for(name, pan=args.pan, tilt=args.tilt, only=only)
        if name == "assembly":
            suffix = "".join(f"_{k}{v:g}" for k, v in (("pan", args.pan), ("tilt", args.tilt)) if v)
            path = args.out / f"assembly{'_detail' if args.only else ''}{suffix}.png"
        else:
            path = args.out / ("parts" if name in PARTS else "hardware") / f"{name}.png"
        render(items, path, name)
        print(f"rendered {name} -> {path}")


if __name__ == "__main__":
    main()
