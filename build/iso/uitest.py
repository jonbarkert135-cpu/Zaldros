#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Stage 2 — in-guest UI validation. Times the interaction chain the spec asks for and samples
CPU/RSS around every step, so "it booted" and "it feels responsive" stay separate verdicts.

Window operations go through KWin's own scripting D-Bus interface, which exists both under full
Plasma and under a bare kwin_wayland session — the same test therefore runs on all three variants.
Steps that genuinely cannot be measured in this environment report {"status": "BLOCKED", "why": ...}
instead of a number. Nothing is estimated.
"""
import json, os, re, shutil, subprocess, time
from pathlib import Path

MARK = "ZALDROS-UITEST "
# The shell publishes the on-screen hit boxes the host-side driver needs (see app.write_hit_boxes).
GEOM_MARK = "ZALDROS-GEOMETRY "
# Printed the moment a *second* toplevel window really exists. Run #37 proved the host driver was
# pressing Alt+Tab while the shell was the only window on screen — the shortcut fired, the KWin
# script ran and honestly logged "candidates=1 / nothing to switch to", and the pixel test called
# that a FAIL. The driver now waits for this line instead of for the geometry, which the shell
# publishes long before any application is up.
WINDOWS_MARK = "ZALDROS-WINDOWS-READY "
KWIN_SCRIPT = """
var out = [];
workspace.windowList().forEach(function (w) {
    out.push({id: String(w.internalId), caption: w.caption, minimized: w.minimized,
              x: w.frameGeometry.x, y: w.frameGeometry.y});
});
console.info("ZALDROS-WINDOWS " + JSON.stringify(out));
"""
TEST_WINDOW_ID = None


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
        entry = dict(detail) if isinstance(detail, dict) else {}
        status = entry.get("status", "PASS" if detail else "FAIL")
        if entry.get("error") or not isinstance(detail, (bool, dict)):
            status = "FAIL"
        entry.update(status=status, seconds=s.seconds, cpu_percent=s.cpu, rss_mib=s.rss)
        results[name] = entry
    except Exception as exc:
        results[name] = {"status": "FAIL", "error": str(exc)}


def wait_for_window(match, timeout=30):
    """A window is 'open' only when KWin reports it, not when the process started."""
    global TEST_WINDOW_ID
    TEST_WINDOW_ID = None
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        found = [w for w in windows() if match.lower() in (w.get("caption") or "").lower()]
        if found and found[0].get("id") not in (None, "", "undefined", "null"):
            TEST_WINDOW_ID = found[0]["id"]
            return {"caption": found[0]["caption"], "window_id": TEST_WINDOW_ID}
        time.sleep(0.5)
    return False


def main():
    results, procs = {}, {}
    variant = Path("/etc/zaldros-variant").read_text().strip() \
        if Path("/etc/zaldros-variant").is_file() else "unknown"

    step("desktop_ready", lambda: bool(windows()), results)
    step("app_launch_explorer",
         lambda: (subprocess.Popen(["dolphin"], stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL), wait_for_window("dolphin"))[1],
         results)
    opened = results["app_launch_explorer"].get("status") == "PASS"
    print(WINDOWS_MARK + json.dumps(
        {"ready": opened, "caption": results["app_launch_explorer"].get("caption"),
         "windows": [w.get("caption") for w in windows()]}, ensure_ascii=False), flush=True)

    # Win+G's screenshot path, measured rather than assumed: the same grabber the shell picks
    # (capture.SCREENSHOT_TOOLS) is run here, and the step passes only if a file appears.
    step("screenshot", lambda: _screenshot(), results)

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


def _screenshot(target=None):
    """Require a successful command and a fresh, decodable image; retain failure diagnostics."""
    from PySide6.QtGui import QImage

    target = Path(target) if target is not None else Path("/tmp/zaldros-shot.png")
    if target.exists():
        target.unlink()
    for command in (["spectacle", "-b", "-n", "-f", "-o", str(target)], ["grim", str(target)]):
        if not shutil.which(command[0]):
            continue
        done = subprocess.run(command, capture_output=True, text=True, timeout=30)
        if done.returncode != 0:
            raise RuntimeError(f"{command[0]} exited {done.returncode}: {(done.stderr or done.stdout).strip()[-1500:]}")
        image = QImage(str(target)) if target.is_file() else QImage()
        if image.isNull() or image.width() <= 0 or image.height() <= 0:
            raise RuntimeError(f"{command[0]} did not create a decodable screenshot: {(done.stderr or done.stdout).strip()[-1500:]}")
        return {"tool": command[0], "bytes": target.stat().st_size,
                "width": image.width(), "height": image.height()}
    raise RuntimeError("no screenshot backend installed (spectacle or grim)")


def _target_window():
    return next((w for w in windows() if TEST_WINDOW_ID and w.get("id") == TEST_WINDOW_ID), None)


def _for_test_window(action):
    """Keep manipulating the same external window after minimizing it changes focus."""
    identity = json.dumps(TEST_WINDOW_ID)
    _kwin_eval("var w = workspace.windowList().filter(function(w) { return String(w.internalId) === "
               + identity + "; })[0]; if (w) { " + action + " }")


def _move():
    before = _target_window()
    if before is None:
        return False
    # Qt's QRectF gadget is a live property reference: changing g.x/g.y issues
    # intermediate requests, then the final assignment can restore the unacked
    # geometry. KWin registers plain JS rectangle conversion; submit one value.
    _for_test_window("var g = w.frameGeometry; w.frameGeometry = "
                     "{x: g.x + 120, y: g.y + 80, width: g.width, height: g.height};")
    time.sleep(0.5)
    after = _target_window()
    if after is None or (before.get("x"), before.get("y")) == (after.get("x"), after.get("y")):
        return False
    return {"window_id": TEST_WINDOW_ID, "before": [before["x"], before["y"]],
            "after": [after["x"], after["y"]]}


def _set_minimized(state):
    before = _target_window()
    if before is None or before.get("minimized") is state:
        return False
    _for_test_window(f"w.minimized = {str(state).lower()};")
    time.sleep(0.5)
    after = _target_window()
    return {"window_id": TEST_WINDOW_ID, "minimized": state} if (
        after is not None and after.get("minimized") is state) else False


if __name__ == "__main__":
    main()
