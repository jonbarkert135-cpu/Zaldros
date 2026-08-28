# SPDX-License-Identifier: GPL-3.0-or-later
"""`python -m zaldros_writer render|run`."""

from __future__ import annotations

import argparse
import sys

from .app import render, run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="zaldros_writer")
    sub = parser.add_subparsers(dest="command", required=True)
    draw = sub.add_parser("render", help="render the window to a PNG")
    draw.add_argument("--out", required=True)
    draw.add_argument("--open", dest="open_path")
    started = sub.add_parser("run", help="open the window")
    started.add_argument("--open", dest="open_path")
    args = parser.parse_args(argv)
    if args.command == "render":
        print(render(args.out, open_path=args.open_path))
        return 0
    return run(args.open_path)


if __name__ == "__main__":
    sys.exit(main())
