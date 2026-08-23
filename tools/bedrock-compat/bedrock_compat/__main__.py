"""CLI: validate the compatibility registries or render them as reports.

    python -m bedrock_compat --check                 # exit 1 if any claim lacks evidence
    python -m bedrock_compat --report hardware       # markdown report
"""
from __future__ import annotations

import argparse
import os
import sys

from .registry import load, to_markdown, validate

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
REGISTRIES = {
    "apps": (os.path.join(DATA_DIR, "applications.json"), "app", "Bedrock Linux — application compatibility"),
    "hardware": (os.path.join(DATA_DIR, "hardware.json"), "hardware", "Bedrock Linux — hardware compatibility matrix"),
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bedrock-compat", description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate every registry")
    parser.add_argument("--report", choices=sorted(REGISTRIES), help="print a markdown report")
    parser.add_argument("--data-dir", default=DATA_DIR)
    args = parser.parse_args(argv)

    if not args.check and not args.report:
        parser.error("choose --check or --report")

    failures = 0
    for key, (path, kind, title) in REGISTRIES.items():
        path = os.path.join(args.data_dir, os.path.basename(path))
        entries = load(path, kind)
        if args.check:
            problems = validate(entries)
            for problem in problems:
                print(f"FAIL [{key}] {problem}", file=sys.stderr)
            failures += len(problems)
            if not problems:
                print(f"ok [{key}] {len(entries)} entries, all claims evidenced", file=sys.stderr)
        if args.report == key:
            sys.stdout.write(to_markdown(entries, title))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
