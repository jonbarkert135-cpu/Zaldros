"""CLI: run the shell, or render evidence screenshots.

    python -m zaldros_shell run
    python -m zaldros_shell render --out ../../docs/evidence/shell-desktop.png
    python -m zaldros_shell render --start --out ../../docs/evidence/shell-start.png
"""
from __future__ import annotations

import argparse

from .app import render, run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="zaldros-shell")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("run")
    r = sub.add_parser("render")
    r.add_argument("--out", required=True)
    r.add_argument("--start", action="store_true", help="render with the Start menu open")
    r.add_argument("--locale", default="ru")
    r.add_argument("--quick", action="store_true", help="render with quick settings open")
    r.add_argument("--context", action="store_true", help="render with the desktop context menu open")
    r.add_argument("--light", action="store_true", help="render the light theme")
    r.add_argument("--search", action="store_true", help="render with the search flyout open")
    r.add_argument("--notifications", action="store_true",
                   help="render with the notification centre open")
    r.add_argument("--clipboard", action="store_true",
                   help="render with the Win+V clipboard flyout open")
    r.add_argument("--game-bar", action="store_true",
                   help="render with the Win+G capture widget open")
    r.add_argument("--window", default="explorer", choices=["explorer", "settings"],
                   help="which application window has focus")
    r.add_argument("--geometry", help="also write the component geometry to this JSON file")
    r.add_argument("--width", type=int, default=1600)
    r.add_argument("--height", type=int, default=1000)
    args = parser.parse_args(argv)

    if args.command == "run":
        return run()
    path = render(args.out, start_open=args.start, width=args.width, height=args.height,
                  locale=args.locale, quick_open=args.quick, context_open=args.context,
                  light=args.light, search_open=args.search,
                  notifications_open=args.notifications, clipboard_open=args.clipboard, game_bar_open=args.game_bar,
                  focused_window=args.window,
                  geometry_output=args.geometry)
    print(f"rendered {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
