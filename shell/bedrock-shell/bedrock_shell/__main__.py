"""CLI: run the shell, or render evidence screenshots.

    python -m bedrock_shell run
    python -m bedrock_shell render --out ../../docs/evidence/shell-desktop.png
    python -m bedrock_shell render --start --out ../../docs/evidence/shell-start.png
"""
from __future__ import annotations

import argparse

from .app import render, run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bedrock-shell")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("run")
    r = sub.add_parser("render")
    r.add_argument("--out", required=True)
    r.add_argument("--start", action="store_true", help="render with the Start menu open")
    r.add_argument("--locale", default="ru")
    r.add_argument("--width", type=int, default=1280)
    r.add_argument("--height", type=int, default=800)
    args = parser.parse_args(argv)

    if args.command == "run":
        return run()
    path = render(args.out, start_open=args.start, width=args.width, height=args.height,
                  locale=args.locale)
    print(f"rendered {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
