"""CLI:

    python -m bedrock_bench collect --label baseline -o baseline.json
    python -m bedrock_bench compare baseline.json candidate.json
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

from .compare import ACCEPT, decide, to_markdown
from .metrics import collect


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bedrock-bench", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    c = sub.add_parser("collect", help="measure this system")
    c.add_argument("--label", default="sample")
    c.add_argument("--build", default="unknown")
    c.add_argument("--commit", default="unknown")
    c.add_argument("--profile", default="desktop")
    c.add_argument("--proc-root", default="/proc")
    c.add_argument("-o", "--output")

    d = sub.add_parser("compare", help="baseline vs candidate → ACCEPT / REVERT / INCONCLUSIVE")
    d.add_argument("baseline")
    d.add_argument("candidate")
    d.add_argument("-o", "--output")
    d.add_argument("--strict", action="store_true", help="exit non-zero unless the verdict is ACCEPT")

    args = parser.parse_args(argv)

    if args.command == "collect":
        sample = collect(args.label, proc_root=args.proc_root, build=args.build,
                         commit=args.commit, profile=args.profile)
        payload = sample.to_json()
        if args.output:
            with open(args.output, "w", encoding="utf-8") as handle:
                handle.write(payload + "\n")
        else:
            print(payload)
        for note in sample.unavailable:
            print(f"unavailable — {note}", file=sys.stderr)
        return 0

    with open(args.baseline, encoding="utf-8") as handle:
        baseline = json.load(handle)
    with open(args.candidate, encoding="utf-8") as handle:
        candidate = json.load(handle)
    verdict, deltas, rationale = decide(baseline.get("metrics", baseline),
                                        candidate.get("metrics", candidate))
    report = to_markdown(verdict, deltas, rationale)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(report)
    else:
        sys.stdout.write(report)
    if args.strict and verdict != ACCEPT:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
