"""Send a part, a hardware item, or the assembly to OCP CAD Viewer in VS Code.

Open the viewer first (OCP CAD Viewer icon in the VS Code activity bar, or
"OCP CAD Viewer: Open viewer" from the command palette); it listens on port 3939.

    uv run harwood0-show                          # the full assembly
    uv run harwood0-show pan_head                 # one printed part or hardware item
    uv run harwood0-show --pan 90 --tilt 30       # pose the camera head
    uv run harwood0-show --only pan_head,tilt_servo,tilt_bracket,camera
"""

import argparse

from ocp_vscode import show

from harwood0_cad.assembly import items_for


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "target", nargs="?", default="assembly", help="'assembly', a part name, or a hardware name"
    )
    parser.add_argument("--only", help="comma-separated assembly item names to include")
    parser.add_argument("--pan", type=float, default=0.0, help="camera pan angle for the assembly")
    parser.add_argument(
        "--tilt", type=float, default=0.0, help="camera tilt angle for the assembly"
    )
    parser.add_argument("--port", type=int, default=None, help="viewer port (default 3939)")
    args = parser.parse_args()

    only = set(args.only.split(",")) if args.only else None
    try:
        items = items_for(args.target, pan=args.pan, tilt=args.tilt, only=only)
    except KeyError as e:
        parser.error(str(e.args[0]))
    show(
        *[i.shape for i in items],
        names=[i.name for i in items],
        colors=[i.color for i in items],
        port=args.port,
    )


if __name__ == "__main__":
    main()
