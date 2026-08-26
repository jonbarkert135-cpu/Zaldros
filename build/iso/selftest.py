#!/usr/bin/env python3
"""In-guest boot self-test. Prints one JSON line, marked so the host can find it on the serial log.

Every check reports what it actually observed; nothing is assumed from a successful build."""
import argparse, json, os, re, subprocess, time
from pathlib import Path

MARK = "ZALDROS-SELFTEST "


def sh(*cmd, timeout=20):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout.strip()
    except Exception as exc:                                  # a failing probe is data, not a crash
        return f"ERROR: {exc}"


def processes():
    out = {}
    for pid in filter(str.isdigit, os.listdir("/proc")):
        try:
            comm = Path(f"/proc/{pid}/comm").read_text().strip()
            rss = int(re.search(r"VmRSS:\s+(\d+)", Path(f"/proc/{pid}/status").read_text())[1])
        except Exception:
            continue
        out.setdefault(comm, [0, 0])
        out[comm][0] += 1
        out[comm][1] += rss
    return out


def mem_used_mib():
    info = dict(re.findall(r"(\w+):\s+(\d+) kB", Path("/proc/meminfo").read_text()))
    return (int(info["MemTotal"]) - int(info["MemAvailable"])) // 1024


def wayland_sockets():
    return sorted(Path("/run/user").glob("*/wayland-*"))


def launch_test(app="konsole"):
    """A real application must actually start and stay alive for two seconds.

    ponytail: the self-test runs as root from systemd, so it must borrow the session user's
    runtime dir and wayland socket — run #16 launched konsole with no display at all."""
    socks = [p for p in wayland_sockets() if not p.name.endswith(".lock")]
    if not socks:
        return {"app": app, "started": False, "error": "no wayland socket"}
    sock = socks[0]
    cmd = ["runuser", "-u", "ubuntu", "--", "env",
           f"XDG_RUNTIME_DIR={sock.parent}", f"WAYLAND_DISPLAY={sock.name}",
           f"DBUS_SESSION_BUS_ADDRESS=unix:path={sock.parent}/bus",
           "QT_QPA_PLATFORM=wayland", app]
    try:
        started = time.monotonic()
        # Keep stderr: run #17 said only "started: false" for services/legacy, which explains nothing.
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        time.sleep(2)
        alive = proc.poll() is None
        out = {"app": app, "started": alive, "seconds": round(time.monotonic() - started, 2)}
        if alive:
            proc.terminate()
        else:
            out["stderr"] = (proc.stderr.read() or "")[-1500:]
            out["exit_code"] = proc.returncode
        return out
    except Exception as exc:
        return {"app": app, "started": False, "error": str(exc)}


def boot_seconds():
    """Real boot time, measured two ways instead of the harness ceiling (which is wall clock of the
    whole QEMU run). uptime_at_selftest = kernel start -> this test; systemd-analyze is often
    unavailable in a live session, so it is reported as null rather than guessed."""
    out = {"uptime_at_selftest_s": None, "systemd_analyze": None,
           "userspace_s": None, "kernel_s": None}
    try:
        out["uptime_at_selftest_s"] = round(float(Path("/proc/uptime").read_text().split()[0]), 2)
    except Exception as exc:
        out["uptime_error"] = str(exc)
    analyze = sh("systemd-analyze", "time")
    if analyze:
        out["systemd_analyze"] = analyze
        import re
        m = re.search(r"([\d.]+)s \(kernel\).*?([\d.]+)s \(userspace\)", analyze, re.S)
        if m:
            out["kernel_s"], out["userspace_s"] = float(m.group(1)), float(m.group(2))
    return out


def settled_systemd_state(timeout=120):
    deadline = time.monotonic() + timeout
    state = sh("systemctl", "is-system-running")
    while state in ("starting", "initializing") and time.monotonic() < deadline:
        time.sleep(3)
        state = sh("systemctl", "is-system-running")
    return state



def visual_layer():
    """Evidence that the installed visual layer is really on disk and picked up.

    The session log has complained about a missing cursor theme since run #17; that stays invisible
    unless the self-test reports it, so it is reported here as fact rather than assumed.
    """
    cursor = ""
    conf = Path("/etc/zaldros/visual.conf")
    if conf.is_file():
        for line in conf.read_text().splitlines():
            key, _, value = line.partition("=")
            if key.strip() == "cursor_theme":
                cursor = value.strip()
    theme_dir = Path("/usr/share/icons") / cursor if cursor else None
    return {
        "cursor_theme": cursor,
        "cursor_theme_installed": bool(theme_dir and theme_dir.is_dir()),
        "cursor_shapes": len(list((theme_dir / "cursors").glob("*"))) if theme_dir and (theme_dir / "cursors").is_dir() else 0,
        "cursor_default_alias": Path("/usr/share/icons/default/index.theme").is_file(),
        "xcursor_theme_env": os.environ.get("XCURSOR_THEME", ""),
        "icon_theme_installed": Path("/usr/share/icons/Zaldros/index.theme").is_file(),
        "icon_theme_apps": len(list(Path("/usr/share/icons/Zaldros/apps/scalable").glob("*.svg")))
                           if Path("/usr/share/icons/Zaldros/apps/scalable").is_dir() else 0,
    }


def tail_file(path, n=4000):
    """Last n chars of a log file, or None when it does not exist (never a guess)."""
    try:
        return Path(path).read_text(errors="replace")[-n:]
    except OSError:
        return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--serial", default="")
    ap.add_argument("--settle", type=float, default=15.0, help="seconds to let the desktop settle")
    ap.add_argument("--wait-kwin", type=float, default=90.0,
                    help="seconds to wait for the compositor before reporting what is there")
    args = ap.parse_args()
    time.sleep(args.settle)
    # The desktop is not up the moment graphical.target is reached; wait for evidence of it,
    # and if it never appears, say so with the session logs attached rather than guessing.
    deadline = time.monotonic() + args.wait_kwin
    while time.monotonic() < deadline and "kwin_wayland" not in processes():
        time.sleep(2)

    procs = processes()
    runtime = os.environ.get("XDG_RUNTIME_DIR", "/run/user/1000")
    result = {
        "variant": Path("/etc/zaldros-variant").read_text().strip()
                   if Path("/etc/zaldros-variant").is_file() else "unknown",
        "kernel": sh("uname", "-r"),
        # is-system-running is "starting" until every job settles; wait for a verdict instead of
        # sampling one too early (run #17 failed the systemd check for exactly that reason).
        "boot_time": boot_seconds(),
        "systemd_state": settled_systemd_state(),
        # Evidence for that state: run #18 sat at "starting" with zero failed units because this
        # very self-test is a job inside the graphical.target transaction.
        "pending_jobs": sh("systemctl", "list-jobs", "--no-legend", "--plain"),
        "failed_units": sh("systemctl", "list-units", "--state=failed", "--no-legend", "--plain"),
        "wayland_socket": [str(p) for p in wayland_sockets()],
        "kwin": "kwin_wayland" in procs,
        "plasmashell": "plasmashell" in procs,
        # ponytail: "python3 is running" was a false positive — this self-test *is* python3.
        # ponytail: pgrep -f zaldros_shell also matched *kwin_wayland's* command line
        # ("kwin_wayland -- python3 -m zaldros_shell"), so run #18 reported shell=true while the
        # shell had already exited. Match the python interpreter process itself.
        "shell": bool(sh("pgrep", "-f", "^python3 -m zaldros_shell")) or "plasmashell" in procs,
        "shell_journal": sh("journalctl", "-u", "zaldros-session.service", "-b", "--no-pager", "-n", "80"),
        "process_count": sum(n for n, _ in procs.values()),
        "mem_used_mib": mem_used_mib(),
        "rss_mib": {c: round(r / 1024, 1) for c, (_, r) in
                    sorted(procs.items(), key=lambda kv: -kv[1][1])[:12]},
        "loadavg": Path("/proc/loadavg").read_text().split()[:3],
        "session_log": tail_file("/tmp/zaldros-session.log"),
        "app_launch": launch_test(),
        "visual_layer": visual_layer(),
        # Session diagnostics: run #15 booted fine but no compositor ever started.
        "sessions_available": sorted(p.name for p in Path("/usr/share/wayland-sessions").glob("*.desktop"))
                              if Path("/usr/share/wayland-sessions").is_dir() else [],
        "users": sh("getent", "passwd", "1000"),
        "runtime_dirs": sorted(p.name for p in Path("/run/user").glob("*")) if Path("/run/user").is_dir() else [],
        "session_unit": sh("systemctl", "show", "zaldros-session.service",
                           "-p", "ActiveState", "-p", "SubState", "-p", "Result", "-p", "ExecMainStatus"),
        "session_journal": sh("journalctl", "-u", "zaldros-session", "--no-pager", "-n", "60")[-4000:],
    }
    # The host-side UI driver starts as soon as this marker appears, and it needs the shell's
    # published hit boxes to click anything. Print them first so they are on the serial log by
    # the time the driver reads it.
    try:
        geometry = json.loads(Path("/tmp/zaldros-ui-geometry.json").read_text())
    except Exception as exc:                                    # noqa: BLE001 - reported, not hidden
        geometry = {"error": str(exc)}
    result["ui_geometry"] = geometry
    geometry_line = "ZALDROS-GEOMETRY " + json.dumps(geometry, ensure_ascii=False)
    print(geometry_line, flush=True)
    line = MARK + json.dumps(result, ensure_ascii=False)
    print(line, flush=True)
    if args.serial:
        with open(args.serial, "w") as fh:
            fh.write(geometry_line + "\n" + line + "\n")


if __name__ == "__main__":
    main()
