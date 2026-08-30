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
    ("boot time", lambda d: boot_time_cell(d.get("boot_time"))),
]


def boot_time_cell(value):
    """One cell out of `selftest.boot_seconds()`, which is a dict, not a line of text.

    It used to be the raw `systemd-analyze time` output, so this column called `.splitlines()`
    on it. When the guest started measuring two ways (uptime at self-test, plus kernel/userspace
    when systemd-analyze answers) the column began raising AttributeError and the whole matrix
    vanished from the run summary. Both shapes are accepted, and "no measurement" prints as a
    dash instead of a guess.
    """
    if isinstance(value, dict):
        kernel, userspace = value.get("kernel_s"), value.get("userspace_s")
        if kernel is not None and userspace is not None:
            return f"{kernel:g}s kernel + {userspace:g}s userspace"
        uptime = value.get("uptime_at_selftest_s")
        if uptime is not None:
            return f"{uptime:g}s to self-test"
        return "—"
    if isinstance(value, str) and value.strip():
        return value.splitlines()[0][:60]
    return "—"


UI_STEPS = ["desktop_ready", "start_open", "start_close", "app_launch_explorer", "window_move",
            "minimize", "restore", "alt_tab", "taskbar_response", "screenshot"]


def ui_cell(d, step):
    """UI verdicts come from two halves: the guest measures window operations, the host measures
    keyboard/mouse interaction by looking at the screen. Whichever half owns the step wins."""
    entries = [source.get(step) for source in
               ((d.get("ui_guest") or {}).get("steps") or {}, d.get("ui_host") or {})]
    entries = [e for e in entries if isinstance(e, dict) and e.get("status")]
    # A measured verdict always beats the other half's "BLOCKED — someone else measures this".
    entries.sort(key=lambda e: e["status"] == "BLOCKED")
    if not entries:
        return "—"
    seconds = entries[0].get("seconds")
    return entries[0]["status"] + (f" {seconds}s" if seconds is not None else "")


def ui_table(rows):
    head = ["image", "profile"] + UI_STEPS
    out = ["", "### UI interaction (stage 2)", "| " + " | ".join(head) + " |",
           "| " + " | ".join("---" for _ in head) + " |"]
    for d in rows:
        out.append("| " + " | ".join([d.get("variant", "?"), d.get("profile", "?")]
                                     + [ui_cell(d, s) for s in UI_STEPS]) + " |")
    return "\n".join(out)


def main(directory="results"):
    # Only the per-boot result files. The other halves (-host, .ui-guest, .late — the last one
    # started landing in results/ when the diagnostics were made to outlive the build, ADR-0024)
    # are read through the boot result, and a name-based exclusion list keeps going stale, so the
    # test is what a boot row actually is: a dict that says which image it came from *and* how the
    # boot went. `variant` alone is not enough — the build manifest carries it too (iso
    # 33327622991 printed a `| full | ? | FAIL |` row from one).
    rows = [d for d in (json.loads(p.read_text()) for p in sorted(Path(directory).glob("*.json")))
            if isinstance(d, dict) and "variant" in d and "boot" in d]
    if not rows:
        print("no results — BLOCKED, nothing ran")
        return 1
    head = ["image", "profile"] + [c for c, _ in COLUMNS]
    print("| " + " | ".join(head) + " |")
    print("| " + " | ".join("---" for _ in head) + " |")
    for d in rows:
        cells = [d.get("variant", "?"), d.get("profile", "?")] + [str(fn(d)) for _, fn in COLUMNS]
        print("| " + " | ".join(cells) + " |")
    print(ui_table(rows))
    # A green CI job must never mean "did not boot".
    return 0 if all(d.get("boot") == "PASS" for d in rows) else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
