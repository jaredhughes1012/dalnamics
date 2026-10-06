"""Send the layout, the assembly, a part, or a hardware item to OCP CAD Viewer in VS Code.

Open the viewer first (OCP CAD Viewer icon in the VS Code activity bar, or
"OCP CAD Viewer: Open viewer" from the command palette); it listens on port 3939.

    uv run harwood0-show                 # robot plus the chassis and arm tower detached beside it
    uv run harwood0-show print           # every printed part on the bed, in a grid
    uv run harwood0-show assembly        # just the finished robot
    uv run harwood0-show track           # one printed part or hardware item
    uv run harwood0-show assembly --pose ground_front
    uv run harwood0-show assembly --only chassis,top_plate,motor_front_left
"""

import argparse
import copy

from build123d import Color, Compound

from harwood0_cad.assembly import Item, items_for, layout


def _group(label: str, items: list[Item]) -> Compound:
    children = []
    for item in items:
        shape = copy.copy(item.shape)
        shape.label = item.name
        shape.color = Color(item.color)
        children.append(shape)
    return Compound(children=children, label=label)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "target",
        nargs="?",
        default="layout",
        help="'layout', 'assembly', 'print', a part, or a hardware name",
    )
    parser.add_argument("--only", help="comma-separated assembly item names to include")
    parser.add_argument("--pose", default="neutral", help="named arm pose for the assembly")
    parser.add_argument("--cables", action="store_true", help="add the cable runs to the assembly")
    parser.add_argument("--port", type=int, default=None, help="viewer port (default 3939)")
    args = parser.parse_args()

    from ocp_vscode import Camera, show

    if args.target == "layout":
        groups = [_group(name, items) for name, items in layout().items()]
    else:
        only = set(args.only.split(",")) if args.only else None
        try:
            groups = [
                _group(
                    args.target,
                    items_for(args.target, only=only, pose=args.pose, cables=args.cables),
                )
            ]
        except KeyError as e:
            parser.error(str(e.args[0]))
    show(*groups, port=args.port, reset_camera=Camera.RESET)


if __name__ == "__main__":
    main()
