"""Fetch the Windows 11 reference library into a local cache.

The library (assets/refs/win11/library.json) lists authentic Windows 11 screenshots published by
Microsoft: what state each one shows, where it came from and its sha256. The images themselves are
Microsoft's copyright, so they are never committed — this script downloads them on demand and
verifies that what arrived is byte-for-byte what was catalogued.

    python3 tools/visual/fetch_references.py            # download what is missing, verify the rest
    python3 tools/visual/fetch_references.py --check    # verify only, download nothing
    python3 tools/visual/fetch_references.py --state quick_settings

Exit code is non-zero when a file is missing (in --check) or a checksum does not match, because a
reference that silently changed underneath us would poison every measurement taken from it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIBRARY = ROOT / "assets" / "refs" / "win11" / "library.json"
CACHE = ROOT / "assets" / "refs" / "win11" / "cache"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"
TIMEOUT = 60


def load_entries(state: str | None) -> list[dict]:
    library = json.loads(LIBRARY.read_text(encoding="utf-8"))
    entries = library["entries"]
    if state:
        entries = [entry for entry in entries if state in entry["states"]]
        if not entries:
            raise SystemExit(f"no library entry covers state {state!r}; "
                             f"known states: {', '.join(library['states'])}")
    return entries


def download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.read()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true",
                        help="verify the cache without downloading anything")
    parser.add_argument("--state", help="only entries covering this state")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    CACHE.mkdir(parents=True, exist_ok=True)
    entries = load_entries(args.state)
    missing: list[str] = []
    corrupt: list[str] = []
    failed: list[str] = []
    fetched = 0

    for entry in entries:
        target = CACHE / entry["file"]
        if not target.exists():
            if args.check:
                missing.append(entry["file"])
                continue
            try:
                payload = download(entry["url"])
            except Exception as error:                      # noqa: BLE001 - report, never guess
                failed.append(f"{entry['file']}: {error}")
                continue
            target.write_bytes(payload)
            fetched += 1
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        if digest != entry["sha256"]:
            corrupt.append(f"{entry['file']}: expected {entry['sha256'][:16]}, got {digest[:16]}")

    if not args.quiet:
        print(f"library: {len(entries)} entries, {fetched} downloaded, cache at {CACHE}")
        for label, items in (("missing", missing), ("checksum mismatch", corrupt),
                             ("download failed", failed)):
            for item in items:
                print(f"  {label}: {item}")
    return 1 if (missing or corrupt or failed) else 0


if __name__ == "__main__":
    sys.exit(main())
