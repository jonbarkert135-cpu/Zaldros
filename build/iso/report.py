#!/usr/bin/env python3
"""Turn boot-test JSON results into the PASS/FAIL matrix the spec asks for."""
import json, sys
from pathlib import Path

COLUMNS = [
    ("boot", lambda d: d.get("boot", "FAIL")),
    ("kernel", lambda d: "PASS " + d["kernel"] if d.get("kernel") else "FAIL"),
    ("systemd", lambda d: "PASS" if d.get("systemd_state") in ("running", "degraded") else "FAIL"),
    ("wayland", lambda d: "PASS" if d.get("wayland_socket") else "FAIL"),
    ("kwin", lambda d: "PASS" if d.get("kwin") else "FAIL"),
    ("shell", lambda d: "PASS" if d.get("shell") else "FAIL"),
    ("app launch", lambda d: "PASS" if (d.get("app_launch") or {}).get("started") else "FAIL"),
    ("RAM MiB", lambda d: d.get("mem_used_mib", "—")),
    ("procs", lambda d: d.get("process_count", "—")),
    ("boot time", lambda d: (d.get("boot_time") or "—").splitlines()[0][:60]),
]


def main(directory="results"):
    rows = [json.loads(p.read_text()) for p in sorted(Path(directory).glob("*.json"))]
    if not rows:
        print("no results — BLOCKED, nothing ran")
        return 1
    head = ["image", "profile"] + [c for c, _ in COLUMNS]
    print("| " + " | ".join(head) + " |")
    print("| " + " | ".join("---" for _ in head) + " |")
    for d in rows:
        cells = [d.get("variant", "?"), d.get("profile", "?")] + [str(fn(d)) for _, fn in COLUMNS]
        print("| " + " | ".join(cells) + " |")
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
