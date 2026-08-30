#!/usr/bin/env python3
"""In-guest boot self-test. Prints one JSON line, marked so the host can find it on the serial log.

Every check reports what it actually observed; nothing is assumed from a successful build."""
import argparse, json, os, re, subprocess, time
from pathlib import Path

MARK = "ZALDROS-SELFTEST "
LATE_MARK = "ZALDROS-LATE "
GEOMETRY_MARK = "ZALDROS-GEOMETRY "
UITEST_MARK = "ZALDROS-UITEST "
WINDOWS_READY_MARK = "ZALDROS-WINDOWS-READY "   # printed by uitest.py once a second window exists


def marked(mark, payload):
    """One marker line whose body can never contain a second marker.

    Run #34: the late report embeds the session log, the session log had already echoed a
    self-test line, and the host's `grep -o 'ZALDROS-SELFTEST {.*' | tail -1` happily picked
    that *escaped* copy — `{\\"kernel\\"...` is not JSON, so every boot job died on a
    JSONDecodeError. Markers appear once per line, at the front, or not at all.
    """
    body = json.dumps(payload, ensure_ascii=False)
    for other in (MARK, LATE_MARK, GEOMETRY_MARK, UITEST_MARK, WINDOWS_READY_MARK):
        body = body.replace(other.strip(), other.strip().replace("ZALDROS-", "ZALDROS_"))
    return mark + body


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



def user_sh(*cmd, timeout=20):
    """Run a command as the session user, on the session bus.

    Run #29 asked kglobalaccel over D-Bus straight from the self-test, which systemd starts as
    root: root has no session bus, so every probe came back empty and the diagnosis said
    "component absent" when it had really said nothing at all. D-Bus questions must be asked
    from inside the session, exactly like launch_test() already does for applications.
    """
    socks = [p for p in wayland_sockets() if not p.name.endswith(".lock")]
    runtime = socks[0].parent if socks else Path("/run/user/1000")
    full = ["runuser", "-u", "ubuntu", "--", "env",
            f"XDG_RUNTIME_DIR={runtime}",
            f"DBUS_SESSION_BUS_ADDRESS=unix:path={runtime}/bus", *cmd]
    try:
        done = subprocess.run(full, capture_output=True, text=True, timeout=timeout)
        out = done.stdout.strip()
        if done.returncode != 0:                              # the error text is the evidence
            out = f"{out}\nEXIT {done.returncode}: {done.stderr.strip()}".strip()
        return out
    except Exception as exc:
        return f"ERROR: {exc}"


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


def switcher():
    """Facts about the Alt+Tab path, because three runs in a row failed it for three different
    reasons and each diagnosis cost a 45-minute image build.

    Nothing here is inferred: what is on disk, what the configuration says, and what
    kglobalaccel reports about KWin's own shortcut."""
    package = Path("/usr/share/kwin/tabbox/zaldros")
    layout = ""
    tabbox = {}
    tabbox_alt = {}
    kwinrc = Path("/etc/xdg/kwinrc")
    if kwinrc.is_file():
        section = ""
        for line in kwinrc.read_text(errors="replace").splitlines():
            line = line.strip()
            if line.startswith("["):
                section = line
            elif "=" in line and section in ("[TabBox]", "[TabBoxAlternative]"):
                key, _, value = line.partition("=")
                target = tabbox if section == "[TabBox]" else tabbox_alt
                target[key.strip()] = value.strip()
        layout = tabbox.get("LayoutName", "")
    runtime = ""
    socks = [q for q in wayland_sockets() if not q.name.endswith(".lock")]
    if socks:
        runtime = str(socks[0].parent)
    shortcut = user_sh("gdbus", "call", "--session", "--dest", "org.kde.kglobalaccel",
                       "--object-path", "/component/kwin",
                       "--method", "org.kde.kglobalaccel.Component.allShortcutInfos")
    # Two entries start with "Walk Through Windows"; the interesting one is the *exact* name,
    # because that is the action Alt+Tab is bound to. Run #33 captured the "of Current
    # Application" entry instead and proved nothing about Alt+Tab.
    walk = ""
    walk_exact = ""
    zaldros_action = ""
    for part in shortcut.split("('"):
        if part.startswith("Walk Through Windows"):
            walk = walk or part[:400]
            if part.startswith("Walk Through Windows', "):
                walk_exact = part[:400]
        # Our own action registers into this same component; its key list is the whole question.
        if part.startswith("Zaldros Walk Through Windows', "):
            zaldros_action = part[:400]
    # Ask kglobalaccel to fire KWin's own shortcut. If this errors, the key never had a chance and
    # the layout is innocent; if it succeeds while Alt+Tab still does nothing, the input path is
    # the suspect. Either way the answer is recorded, not guessed.
    invoked = user_sh("gdbus", "call", "--session", "--dest", "org.kde.kglobalaccel",
                      "--object-path", "/component/kwin",
                      "--method", "org.kde.kglobalaccel.Component.invokeShortcut",
                      "Walk Through Windows")
    names = user_sh("gdbus", "call", "--session", "--dest", "org.freedesktop.DBus",
                    "--object-path", "/org/freedesktop/DBus",
                    "--method", "org.freedesktop.DBus.ListNames")
    kde_names = sorted({n for n in re.findall(r"'([^']+)'", names) if "kde" in n.lower()})
    return {
        "package_installed": package.is_dir(),
        "accel_path": Path("/etc/zaldros/accel-path").read_text().strip()
                      if Path("/etc/zaldros/accel-path").is_file() else "",
        "accel_running": sh("pgrep", "-a", "kglobalacceld"),
        "session_bus_socket": bool(runtime) and Path(runtime, "bus").exists(),
        "runtime_dir": runtime,
        "dbus_kde_names": kde_names,
        "all_components": user_sh("gdbus", "call", "--session", "--dest", "org.kde.kglobalaccel",
                                  "--object-path", "/kglobalaccel",
                                  "--method", "org.kde.KGlobalAccel.allComponents")[:400],
        "invoke_shortcut_reply": invoked[:300],
        "package_files": sorted(str(f.relative_to(package)) for f in package.rglob("*") if f.is_file())
                         if package.is_dir() else [],
        "installed_layouts": sorted(p.name for p in Path("/usr/share/kwin/tabbox").iterdir())
                             if Path("/usr/share/kwin/tabbox").is_dir() else [],
        "configured_layout": layout,
        "tabbox_config": tabbox,
        "tabbox_alternative_config": tabbox_alt,
        "kglobalaccel_component_present": bool(walk) or "Walk Through Windows" in shortcut,
        "all_shortcut_infos_error": shortcut[:300] if not walk else "",
        "walk_through_windows": walk,
        "walk_through_windows_exact": walk_exact,
        "zaldros_action": zaldros_action,
        "kwin_journal": sh("sh", "-c",
                           "journalctl -b --no-pager | grep -iE 'tabbox|switcher|kwin_tabbox' | tail -n 20"),
    }


def tail_file(path, n=4000):
    """Last n chars of a log file, or None when it does not exist (never a guess)."""
    try:
        return Path(path).read_text(errors="replace")[-n:]
    except OSError:
        return None


def kwin_environ(name):
    """One variable out of the live compositor's environment — proof, not assumption.

    A logging category that was exported by the session script but never reached kwin looks
    exactly like a category that produced no output, and run #34 could not tell them apart.
    """
    pid = sh("pgrep", "-x", "kwin_wayland").split("\n")[0].strip()
    if not pid.isdigit():
        return "no kwin_wayland process"
    try:
        blob = Path(f"/proc/{pid}/environ").read_bytes().decode(errors="replace")
    except OSError as exc:
        return f"ERROR: {exc}"
    for entry in blob.split("\0"):
        if entry.startswith(name + "="):
            return entry[len(name) + 1:]
    return f"{name} not set for kwin"


def shortcut_lines(pattern="Walk Through"):
    """Every configured shortcut line matching pattern, from the file kglobalaccel actually uses.

    Run #35 read only the tail of that file and could not see whether KWin's own Alt+Tab entry
    had survived; the answer to "who holds the key" must never depend on a byte budget.
    """
    out = {}
    for path in ("/home/ubuntu/.config/kglobalshortcutsrc", "/etc/xdg/kglobalshortcutsrc"):
        try:
            text = Path(path).read_text(errors="replace")
        except OSError as exc:
            out[path] = f"ERROR: {exc}"
            continue
        out[path] = [line for line in text.splitlines()
                     if pattern.lower() in line.lower() or line.startswith("[")][:60]
    return out


def invoke_and_watch(action="Zaldros Walk Through Windows", component="kwin"):
    """Fire the switch over D-Bus and report exactly what the session log gained.

    This separates the two ways Alt+Tab can be broken: the key never reaching a shortcut, or the
    shortcut running and drawing nothing. The key press is the host's job; this is the other half.
    """
    log = Path("/tmp/zaldros-session.log")
    before = log.stat().st_size if log.is_file() else 0
    # Run #35: /kglobalaccel has no invokeShortcut. The method lives on the *component* object
    # (org.kde.kglobalaccel.Component), and our action registers into the kwin component, so that
    # is the only address that can fire it.
    reply = user_sh("gdbus", "call", "--session", "--dest", "org.kde.kglobalaccel",
                    "--object-path", f"/component/{component}", "--method",
                    "org.kde.kglobalaccel.Component.invokeShortcut", action)
    time.sleep(1.5)
    after = ""
    if log.is_file():
        with open(log, errors="replace") as fh:
            fh.seek(before)
            after = fh.read()[:4000]
    return {"component": component, "action": action, "reply": reply, "log_gained": after}


def late_report():
    """Everything that only exists *after* the host has pressed Alt+Tab.

    KWin writes one warning when the switcher package will not load and one debug line per tabbox
    show; both land in the session log, which the boot self-test reads 100 seconds too early.
    """
    log = Path("/tmp/zaldros-session.log")
    text = log.read_text(errors="replace") if log.is_file() else ""
    interesting = [line for line in text.splitlines()
                   if re.search(r"tabbox|switcher|TabBox|QQmlComponent|is not installed|"
                                r"Component failed|module .* not installed", line, re.I)]
    return {
        "session_log_tail": text[-6000:],
        "tabbox_lines": interesting[-40:],
        "switcher_script_lines": [line for line in text.splitlines()
                                  if "ZALDROS_SWITCHER" in line or "ZALDROS-SWITCHER" in line][-40:],
        # Which key presses reached a global shortcut at all. Read *before* invoke_and_watch fires
        # one over D-Bus, so every line here was produced by a real key from the host.
        "probe_lines": [line.split("ZALDROS")[1] for line in text.splitlines()
                        if "ZALDROS-PROBE" in line or "ZALDROS_PROBE" in line][-20:],
        # The switcher's own verdict, in its own words: how many windows it saw and whether it
        # activated one. A key that fires but finds a single window is not a broken shortcut.
        "switcher_cycles": [line.split("ZALDROS-SWITCHER ", 1)[-1] for line in text.splitlines()
                            if "ZALDROS-SWITCHER" in line and ("cycle reverse" in line
                                                               or "activating" in line
                                                               or "nothing to switch" in line)][-20:],
        "alt_tab_switched": any("ZALDROS-SWITCHER" in line and "activating" in line
                                for line in text.splitlines()),
        "shortcut_fired_by_key": any(("ZALDROS-SWITCHER" in line or "ZALDROS_SWITCHER" in line)
                                     and "cycle reverse" in line for line in text.splitlines()),
        "kwin_logging_rules": kwin_environ("QT_LOGGING_RULES"),
        "invoke_delta": invoke_and_watch(),
        "qml_import_paths": sh("sh", "-c",
                               "ls -d /usr/lib/x86_64-linux-gnu/qt6/qml/QtQuick* 2>&1 | head -n 20"),
        "kwin_scripts_installed": sh("sh", "-c", "ls /usr/share/kwin/scripts 2>&1"),
        "user_shortcuts_file": tail_file("/home/ubuntu/.config/kglobalshortcutsrc", 1200),
        "shortcut_lines": shortcut_lines(),
        "switcher": switcher(),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--serial", default="")
    ap.add_argument("--late", action="store_true",
                    help="run after the host UI drive and report what KWin logged then")
    ap.add_argument("--settle", type=float, default=15.0, help="seconds to let the desktop settle")
    ap.add_argument("--wait-kwin", type=float, default=90.0,
                    help="seconds to wait for the compositor before reporting what is there")
    args = ap.parse_args()
    if args.late:
        line = marked(LATE_MARK, late_report())
        print(line, flush=True)
        if args.serial:
            with open(args.serial, "w") as fh:
                fh.write(line + "\n")
        return
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
        "switcher": switcher(),
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
    geometry_line = marked(GEOMETRY_MARK, geometry)
    print(geometry_line, flush=True)
    line = marked(MARK, result)
    print(line, flush=True)
    if args.serial:
        with open(args.serial, "w") as fh:
            fh.write(geometry_line + "\n" + line + "\n")


if __name__ == "__main__":
    main()
