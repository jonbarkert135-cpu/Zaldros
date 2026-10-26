#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Turn boot-test JSON results into the PASS/FAIL matrix the spec asks for."""
import argparse
import json
import sys
from pathlib import Path

COLUMNS = [
    ("boot", lambda d: d.get("boot", "FAIL")),
    ("kernel", lambda d: "PASS " + d["kernel"] if d.get("kernel") else "FAIL"),
    ("systemd", lambda d: "PASS" if boot_checks(d)["systemd"] else "FAIL"),
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
            "minimize", "restore", "alt_tab", "task_view", "taskbar_response", "screenshot"]
HOST_STEPS = {"start_open", "start_close", "alt_tab", "task_view", "taskbar_response"}


def boot_checks(data):
    """Shared by the boot producer and report consumer; a label cannot replace facts."""
    pending = [line.split() for line in str(data.get("pending_jobs") or "").splitlines()
               if line.strip()]
    only_own_jobs = bool(pending) and all(
        len(parts) >= 2 and parts[1] in {"zaldros-selftest.service", "graphical.target"}
        for parts in pending)
    no_failed_units = not str(data.get("failed_units") or "").strip()
    state = data.get("systemd_state")
    launch = data.get("app_launch")
    return {
        "kernel": bool(data.get("kernel")),
        "systemd": no_failed_units and (state in ("running", "degraded") or (
            state == "starting" and only_own_jobs)),
        "wayland": bool(data.get("wayland_socket")),
        "kwin": data.get("kwin") is True,
        "shell": data.get("shell") is True,
        "app_launch": isinstance(launch, dict) and launch.get("started") is True,
    }


def ui_sources(data):
    guest = data.get("ui_guest")
    guest = guest.get("steps") if isinstance(guest, dict) else None
    host = data.get("ui_host")
    return (guest if isinstance(guest, dict) else {}, host if isinstance(host, dict) else {})


def ui_result(data, step):
    """Each mandatory step has an owner. Another observer's failure is never discarded."""
    guest, host = ui_sources(data)
    for source in (guest, host):
        entry = source.get(step)
        if isinstance(entry, dict) and entry.get("error"):
            return {**entry, "status": "FAIL"}
        if isinstance(entry, dict) and entry.get("status") in ("FAIL", "ERROR", "TIMEOUT"):
            return entry
    entry = (host if step in HOST_STEPS else guest).get(step)
    return entry if isinstance(entry, dict) else {"status": "MISSING"}


def ui_cell(d, step):
    """Show the same owner/failure verdict that controls acceptance."""
    entry = ui_result(d, step)
    seconds = entry.get("seconds")
    return str(entry.get("status", "MISSING")) + (f" {seconds}s" if seconds is not None else "")


def acceptance_failures(data):
    failures = []
    if data.get("boot") != "PASS":
        failures.append("boot is not PASS")
    failures.extend(f"boot {name}: FAIL" for name, ok in boot_checks(data).items() if not ok)
    if data.get("failed_checks"):
        failures.append(f"producer failed_checks: {data['failed_checks']}")
    checks = data.get("checks")
    if isinstance(checks, dict):
        failures.extend(f"producer boot {name}: not PASS" for name in boot_checks(data)
                        if checks.get(name) is not True)
    for step in UI_STEPS:
        entry = ui_result(data, step)
        status = entry.get("status", "MISSING")
        if status != "PASS":
            reason = str(entry.get("error") or entry.get("why") or "").replace("\n", " ")[:500]
            failures.append(f"UI {step}: {status}" + (f" ({reason})" if reason else ""))
    for name in ("ui_guest", "ui_host"):
        source = data.get(name)
        if isinstance(source, dict):
            if source.get("status") in ("FAIL", "ERROR", "TIMEOUT") or source.get("error"):
                failures.append(f"{name}: failure/error recorded")
    for source in ui_sources(data):
        for step, entry in source.items():
            if step not in UI_STEPS and isinstance(entry, dict) and entry.get("status") in (
                    "FAIL", "ERROR", "TIMEOUT"):
                failures.append(f"UI diagnostic {step}: {entry['status']}")
            elif step not in UI_STEPS and isinstance(entry, dict) and entry.get("error"):
                failures.append(f"UI diagnostic {step}: error recorded")
    host = data.get("ui_host")
    if isinstance(host, dict) and host.get("qmp_errors"):
        failures.append("QMP command errors recorded")
    guest = data.get("ui_guest")
    if isinstance(guest, dict) and guest.get("variant", data.get("variant")) != data.get("variant"):
        failures.append("guest UI report belongs to a different variant")
    return failures


def ui_table(rows):
    head = ["image", "profile"] + UI_STEPS
    out = ["", "### UI interaction (stage 2)", "| " + " | ".join(head) + " |",
           "| " + " | ".join("---" for _ in head) + " |"]
    for d in rows:
        out.append("| " + " | ".join([d.get("variant", "?"), d.get("profile", "?")]
                                     + [ui_cell(d, s) for s in UI_STEPS]) + " |")
    return "\n".join(out)


def main(directory="results", variant=None, profile=None):
    # Only the per-boot result files. The other halves (-host, .ui-guest, .late — the last one
    # started landing in results/ when the diagnostics were made to outlive the build, ADR-0024)
    # are read through the boot result, and a name-based exclusion list keeps going stale, so the
    # test is what a boot row actually is: a dict that says which image it came from *and* how the
    # boot went. `variant` alone is not enough — the build manifest carries it too (iso
    # 33327622991 printed a `| full | ? | FAIL |` row from one).
    rows = []
    for path in sorted(Path(directory).glob("*.json")):
        try:
            data = json.loads(path.read_text())
        except (ValueError, OSError) as exc:
            print(f"invalid report {path.name}: {exc}")
            return 1
        if isinstance(data, dict) and "variant" in data and "boot" in data:
            rows.append(data)
    if not rows:
        print("no valid boot reports — acceptance cannot pass")
        return 1
    identities = [(d.get("variant"), d.get("profile")) for d in rows]
    if any(not isinstance(v, str) or not isinstance(p, str) for v, p in identities):
        print("invalid report identity: variant/profile must be strings")
        return 1
    if len(set(identities)) != len(identities):
        print("duplicate boot targets — refusing stale or conflicting reports")
        return 1
    if variant is not None or profile is not None:
        if identities != [(variant, profile)]:
            print(f"expected exactly {variant}/{profile}, found {identities}")
            return 1
    head = ["image", "profile"] + [c for c, _ in COLUMNS]
    print("| " + " | ".join(head) + " |")
    print("| " + " | ".join("---" for _ in head) + " |")
    for d in rows:
        cells = [d.get("variant", "?"), d.get("profile", "?")] + [str(fn(d)) for _, fn in COLUMNS]
        print("| " + " | ".join(cells) + " |")
    print(ui_table(rows))
    failures = [f"{d.get('variant')}/{d.get('profile')}: {failure}"
                for d in rows for failure in acceptance_failures(d)]
    if failures:
        print("\nAcceptance: FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("\nAcceptance: PASS (boot + required UI steps; hardware/frame pacing not certified)")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", nargs="?", default="results")
    parser.add_argument("--variant", choices=("full", "services", "legacy"))
    parser.add_argument("--profile", choices=("low", "mid", "modern"))
    args = parser.parse_args()
    if bool(args.variant) != bool(args.profile):
        parser.error("--variant and --profile must be provided together")
    sys.exit(main(args.directory, args.variant, args.profile))
