"""CLI: run Zaldros Sheets, or render it for visual evidence."""
from __future__ import annotations

import argparse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="zaldros-sheets")
    sub = parser.add_subparsers(dest="command", required=True)
    r = sub.add_parser("render")
    r.add_argument("--out", required=True)
    r.add_argument("--open", dest="open_path")
    r.add_argument("--dark", action="store_true")
    r.add_argument("--width", type=int, default=1280)
    r.add_argument("--height", type=int, default=800)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--open", dest="open_path")
    args = parser.parse_args(argv)

    from .app import render, run

    if args.command == "run":
        return run(args.open_path)
    print(f"rendered {render(args.out, open_path=args.open_path, light=not args.dark, width=args.width, height=args.height)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
