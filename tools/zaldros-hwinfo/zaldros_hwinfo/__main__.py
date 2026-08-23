"""CLI: python -m zaldros_hwinfo [--format markdown|json] [-o FILE]"""
from __future__ import annotations

import argparse
import sys

from .hwinfo import collect, to_json, to_markdown


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="zaldros-hwinfo", description=__doc__)
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("-o", "--output")
    parser.add_argument("--sysfs", default="/sys", help="override sysfs root (testing)")
    parser.add_argument("--proc", default="/proc", help="override procfs root (testing)")
    args = parser.parse_args(argv)

    inventory = collect(args.sysfs, args.proc)
    text = to_json(inventory) if args.format == "json" else to_markdown(inventory)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(text)
        print(f"wrote {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
