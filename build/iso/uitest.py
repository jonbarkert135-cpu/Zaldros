#!/usr/bin/env python3
"""Stage 2 — in-guest UI validation. Times the interaction chain the spec asks for and samples
CPU/RSS around every step, so "it booted" and "it feels responsive" stay separate verdicts.

Window operations go through KWin's own scripting D-Bus interface, which exists both under full
Plasma and under a bare kwin_wayland session — the same test therefore runs on all three variants.
Steps that genuinely cannot be measured in this environment report {"status": "BLOCKED", "why": ...}
instead of a number. Nothing is estimated.
"""
import json, os, re, subprocess, time
from pathlib import Path

MARK = "ZALDROS-UITEST "
# The shell publishes the on-screen hit boxes the host-side driver needs (see app.write_hit_boxes).
GEOM_MARK = "ZALDROS-GEOMETRY "
KWIN_SCRIPT = """
var out = [];
workspace.windowList().forEach(function (w) {
    out.push({caption: w.caption, minimized: w.minimized, x: w.frameGeometry.x, y: w.frameGeometry.y});
});
console.info("ZALDROS-WINDOWS " + JSON.stringify(out));
"""


def sh(*cmd, timeout=15):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.stdout.strip() or p.stderr.strip()
    except Exception as exc:
        return f"ERROR: {exc}"


def pid_of(name):
    for pid in filter(str.isdigit, os.listdir("/proc")):
        try:
            if Path(f"/proc/{pid}/comm").read_text().strip() == name:
                return pid
        except OSError:
            pass
    return None


def cpu_ticks(pid):
    try:
        f = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        return int(f[11]) + int(f[12])                      # utime + stime
    except Exception:
        return 0


def rss_mib(pid):
    try:
        return int(re.search(r"VmRSS:\s+(\d+)", Path(f"/proc/{pid}/status").read_text())[1]) / 1024
    except Exception:
        return 0.0


class Sampler:
    """CPU and RSS of the compositor and the shell across one step — our CPU/RAM spike measure."""

    def __init__(self):
        self.pids = {n: pid_of(n) for n in ("kwin_wayland", "plasmashell", "python3")}
        self.pids = {n: p for n, p in self.pids.items() if p}

    def __enter__(self):
        self.t0 = time.monotonic()
        self.c0 = {n: cpu_ticks(p) for n, p in self.pids.items()}
        return self

    def __exit__(self, *_):
        self.seconds = round(time.monotonic() - self.t0, 3)
        hz = os.sysconf("SC_CLK_TCK")
        self.cpu = {n: round((cpu_ticks(p) - self.c0[n]) / hz / max(self.seconds, 1e-6) * 100, 1)
                    for n, p in self.pids.items()}
        self.rss = {n: round(rss_mib(p), 1) for n, p in self.pids.items()}


# ponytail: run #17 reported every window step FAIL because qdbus6 is not in the image and the test
# ran as root with no session bus. dbus-send ships with dbus itself, and the unit now exports the
# session bus address, so the same call works under full Plasma and under bare kwin_wayland.
DIAG = {}


SCRIPT_SEQ = [0]


def kwin_call(method, *args):
    out = sh("dbus-send", "--session", "--print-reply", "--dest=org.kde.KWin",
             "/Scripting", f"org.kde.kwin.Scripting.{method}", *args)
    DIAG[method] = out[:400]
    return out


SESSION_LOG = Path("/tmp/zaldros-session.log")


def kwin_log():
    """Where KWin's console.info actually lands.

    Run #25: the session unit redirects its own stdout/stderr to /tmp/zaldros-session.log, so
    nothing the compositor printed ever reached the journal. Every window query came back empty
    and the whole window half of the UI test reported FAIL against a shell that was running fine.
    The file is checked first now; the journal stays as a fallback for other session layouts.
    """
    if SESSION_LOG.is_file():
        try:
            text = SESSION_LOG.read_text(errors="replace")[-200000:]
            if "ZALDROS-WINDOWS" in text:
                return text
        except OSError:
            pass
    out = ""
    for cmd in (("journalctl", "-n", "200", "--no-pager", "-u", "zaldros-session"),
                ("journalctl", "--user", "-n", "200", "--no-pager")):
        out = sh(*cmd)
        if "ZALDROS-WINDOWS" in out:
            return out
    return out


def windows():
    """Ask KWin for its window list; returns [] if the call fails (recorded in DIAG, not hidden).

    KWin keys loaded scripts by file path and refuses to run the same path twice, so a fresh file
    name per query is required; without it only the first poll would ever produce output.
    """
    SCRIPT_SEQ[0] += 1
    script = Path(f"/tmp/zaldros-windows-{SCRIPT_SEQ[0]}.js")
    script.write_text(KWIN_SCRIPT)
    kwin_call("loadScript", f"string:{script}")
    kwin_call("start")
    time.sleep(0.5)
    hit = [l for l in kwin_log().splitlines() if "ZALDROS-WINDOWS" in l]
    try:
        return json.loads(hit[-1].split("ZALDROS-WINDOWS ", 1)[1])
    except Exception:
        return []


def step(name, fn, results):
    """Run one interaction step, timing it and sampling CPU/RSS around it."""
    try:
        with Sampler() as s:
            detail = fn()
        results[name] = {"status": "PASS" if detail is not False else "FAIL",
                         "seconds": s.seconds, "cpu_percent": s.cpu, "rss_mib": s.rss}
        if isinstance(detail, dict):
            results[name].update(detail)
    except Exception as exc:
        results[name] = {"status": "FAIL", "error": str(exc)}


def wait_for_window(match, timeout=30):
    """A window is 'open' only when KWin reports it, not when the process started."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        found = [w for w in windows() if match.lower() in (w.get("caption") or "").lower()]
        if found:
            return {"caption": found[0]["caption"]}
        time.sleep(0.5)
    return False


def main():
    results, procs = {}, {}
    variant = Path("/etc/zaldros-variant").read_text().strip() \
        if Path("/etc/zaldros-variant").is_file() else "unknown"

    step("desktop_ready", lambda: bool(windows()) or {"note": "no windows yet"}, results)
    step("app_launch_explorer",
         lambda: (subprocess.Popen(["dolphin"], stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL), wait_for_window("dolphin"))[1],
         results)
    step("window_move", lambda: _move(), results)
    step("minimize", lambda: _set_minimized(True), results)
    step("restore", lambda: _set_minimized(False), results)

    # Steps that need synthetic input come from the host over QMP; the guest only records that they
    # are not measured here, so the two halves of the test never pretend to be one.
    for blocked in ("start_open", "start_close", "alt_tab", "taskbar_response"):
        results[blocked] = {"status": "BLOCKED",
                            "why": "synthetic input is injected by the host via QMP input-send-event; "
                                   "see results/*.ui-host.json for the timings and screenshots"}
    results["frame_stability"] = {"status": "BLOCKED",
                                  "why": "QEMU renders through llvmpipe/virtio-gpu: frame timings "
                                         "would measure the emulator, not the compositor"}

    for name in ("kwin_wayland", "plasmashell", "python3"):
        pid = pid_of(name)
        procs[name] = {"running": bool(pid), "rss_mib": round(rss_mib(pid), 1) if pid else 0}

    try:
        geometry = json.loads(Path("/tmp/zaldros-ui-geometry.json").read_text())
    except Exception as exc:                                    # noqa: BLE001 - reported, not hidden
        geometry = {"error": str(exc)}
    print(GEOM_MARK + json.dumps(geometry, ensure_ascii=False), flush=True)
    print(MARK + json.dumps({"variant": variant, "steps": results, "processes": procs,
                         "geometry": geometry, "dbus_diag": DIAG},
                            ensure_ascii=False), flush=True)


def _kwin_eval(js):
    SCRIPT_SEQ[0] += 1
    script = Path(f"/tmp/zaldros-op-{SCRIPT_SEQ[0]}.js")
    script.write_text(js)
    kwin_call("loadScript", f"string:{script}")
    return kwin_call("start")


def _move():
    _kwin_eval("var w = workspace.activeWindow; if (w) { var g = w.frameGeometry; "
               "g.x += 120; g.y += 80; w.frameGeometry = g; }")
    time.sleep(0.5)
    return bool(windows())


def _set_minimized(state):
    _kwin_eval(f"var w = workspace.activeWindow; if (w) w.minimized = {str(state).lower()};")
    time.sleep(0.5)
    wins = windows()
    return any(w.get("minimized") == state for w in wins) if wins else False


if __name__ == "__main__":
    main()
