#!/usr/bin/env python3
"""Pull one marked JSON report off a serial log — the last one that actually parses.

The serial log is a shared console: getty prompts, kernel messages and the guest's own logs
land on it interleaved, and a report can quote an older report (escaped) inside itself. So we
do not trust "the last text after the marker"; we try every candidate, newest first, and take
the first one that is valid JSON. Nothing is guessed: if none parse, we exit non-zero and say
how many candidates were seen.
"""
import argparse, json, sys
from pathlib import Path


def candidates(text, mark):
    """Every marker occurrence in the log, newest first, cut to the end of its line."""
    out = []
    for line in text.splitlines():
        idx = line.find(mark)
        while idx != -1:
            out.append(line[idx + len(mark):].strip())
            idx = line.find(mark, idx + len(mark))
    return list(reversed(out))


def extract(text, mark):
    """The newest candidate that is valid JSON, or None."""
    for candidate in candidates(text, mark):
        try:
            return json.loads(candidate)
        except ValueError:
            continue
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("serial")
    ap.add_argument("mark", help="marker prefix, e.g. 'ZALDROS-SELFTEST '")
    ap.add_argument("--out", required=True)
    ap.add_argument("--optional", action="store_true", help="write nothing and exit 0 when absent")
    args = ap.parse_args()

    text = Path(args.serial).read_text(errors="replace")
    data = extract(text, args.mark)
    if data is None:
        seen = len(candidates(text, args.mark))
        print(f"no parsable {args.mark.strip()} report ({seen} candidate(s))", file=sys.stderr)
        return 0 if args.optional else 1
    Path(args.out).write_text(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
