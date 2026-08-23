"""CLI entry point: python -m zaldros_sysprobe [--json|--markdown] [-o FILE]"""
from __future__ import annotations

import argparse
import sys

from .probe import collect, to_json, to_markdown


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="zaldros-sysprobe", description=__doc__)
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("-o", "--output", help="write to a file instead of stdout")
    parser.add_argument("--unit", action="append", help="inspect only these units (repeatable)")
    args = parser.parse_args(argv)

    services = collect(args.unit)
    if not services:
        print("zaldros-sysprobe: no systemd services found (is this a systemd system?)", file=sys.stderr)
        return 1
    text = to_json(services) if args.format == "json" else to_markdown(services)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(text)
        print(f"wrote {args.output} ({len(services)} services)", file=sys.stderr)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
