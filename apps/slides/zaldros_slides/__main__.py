# SPDX-License-Identifier: GPL-3.0-or-later
"""`python -m zaldros_slides render --out slides.png [--open deck.pptx]`."""

from __future__ import annotations

import argparse
import sys

from .app import render


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="zaldros_slides")
    sub = parser.add_subparsers(dest="command", required=True)
    draw = sub.add_parser("render")
    draw.add_argument("--out", required=True)
    draw.add_argument("--open", dest="open_path")
    args = parser.parse_args(argv)
    print(render(args.out, open_path=args.open_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
