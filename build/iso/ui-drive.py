#!/usr/bin/env python3
"""Stage 2, host half — drive the guest's UI over QMP and time what actually changes on screen.

QEMU's `input-send-event` injects real key and mouse events, and `screendump` captures the composited
framebuffer. A step counts as PASS only when the screen visibly changes; a keypress that changes
nothing is a FAIL, not a pass.
"""
import argparse, json, socket, struct, subprocess, time
from pathlib import Path


class QMPError(RuntimeError):
    """QEMU refused a command. Runs #29-#36 never saw one of these because the reply was dropped."""


class QMP:
    def __init__(self, path):
        self.sock = socket.socket(socket.AF_UNIX)
        self.sock.connect(path)
        self.file = self.sock.makefile("rw")
        self.file.readline()                                   # greeting
        self.errors = []
        self.cmd("qmp_capabilities")

    def cmd(self, name, **args):
        """Send one QMP command and *check the reply*.

        Run #36 spent four image builds on a dead Alt+Tab. The cause was here: QKeyCode has no
        `alt_l` (the modifiers are `alt`, `alt_r`, `ctrl`, `ctrl_r`, `shift`, `shift_r`,
        `meta_l`, `meta_r`), so every attempt to hold Alt came back
        `GenericError: Invalid parameter 'alt_l'` — and this method threw the reply away. The
        guest only ever received a bare Tab, and the boot report blamed KWin, kglobalaccel and
        the keyboard layout in turn. An error is now raised, recorded, and reported.
        """
        self.file.write(json.dumps({"execute": name, "arguments": args or {}}) + "\n")
        self.file.flush()
        while True:
            reply = json.loads(self.file.readline())
            if "event" in reply:
                continue
            if "error" in reply:
                message = f"{name}: {reply['error'].get('class')}: {reply['error'].get('desc')}"
                self.errors.append(message)
                raise QMPError(message)
            return reply

    def key(self, *keys):
        events = [{"type": "key", "data": {"down": d, "key": {"type": "qcode", "data": k}}}
                  for d in (True, False) for k in (keys if d else reversed(keys))]
        self.cmd("input-send-event", events=events)

    def key_state(self, key, down):
        """One key down or up, so a modifier can be *held* across screenshots."""
        self.cmd("input-send-event", events=[
            {"type": "key", "data": {"down": down, "key": {"type": "qcode", "data": key}}}])

    def click(self, x, y, width, height):
        absolute = lambda v, span: int(v / span * 0x7FFF)
        self.cmd("input-send-event", events=[
            {"type": "abs", "data": {"axis": "x", "value": absolute(x, width)}},
            {"type": "abs", "data": {"axis": "y", "value": absolute(y, height)}}])
        self.cmd("input-send-event", events=[
            {"type": "btn", "data": {"down": True, "button": "left"}},
            {"type": "btn", "data": {"down": False, "button": "left"}}])

    def screendump(self, path):
        self.cmd("screendump", filename=str(Path(path).resolve()))


def ppm_pixels(path):
    data = Path(path).read_bytes()
    parts = data.split(b"\n", 3)
    return parts[3] if len(parts) > 3 else b""


def changed_fraction(before, after):
    """Fraction of sampled bytes that differ between two frames.

    A mean-brightness comparison (run #25) hides a Start menu that opens and closes again, and it
    calls a one-pixel difference a change. Counting differing bytes is both stricter and honest
    about how much of the screen moved.
    """
    a, b = ppm_pixels(before), ppm_pixels(after)
    if not a or not b or len(a) != len(b):
        return 1.0 if a != b else 0.0
    sample = range(0, len(a), 101)
    differing = sum(1 for i in sample if a[i] != b[i])
    return round(differing / max(len(range(0, len(a), 101)), 1), 5)


CHANGE_THRESHOLD = 0.002        # 0.2 % of sampled bytes; larger than PPM/encoder noise


def timed_step(qmp, out, name, action, settle=1.5):
    before = out / f"{name}-before.ppm"
    after = out / f"{name}-after.ppm"
    qmp.screendump(before)
    started = time.monotonic()
    try:
        action()
    except QMPError as exc:                      # never silent: a refused key is a failed step
        return {"status": "FAIL", "qmp_error": str(exc)}
    time.sleep(settle)
    qmp.screendump(after)
    elapsed = round(time.monotonic() - started, 3)
    try:
        fraction = changed_fraction(before, after)
    except Exception as exc:
        return {"status": "FAIL", "error": str(exc)}
    changed = fraction >= CHANGE_THRESHOLD
    return {"status": "PASS" if changed else "FAIL", "seconds": elapsed,
            "screen_changed": changed, "changed_fraction": fraction,
            "screenshot": after.name}


def alt_tab_step(qmp, out, settle=1.2, modifier="alt", prefix="alt_tab"):
    """Alt+Tab the way a person does it: hold Alt, tap Tab, *look at the screen*, then let go.

    Run #29 pressed and released in one batch and could only see the aftermath, which made a
    switcher that never drew indistinguishable from one that drew and vanished. Three frames are
    taken instead: before, with Alt still held, and after release — and the verdict about the
    switcher is `alt_tab_verdict`'s, not a single fraction's.

    Meta+Tab is driven by the same code with `modifier="meta_l"`: it opens KWin's *alternative*
    tabbox, which we dress as the Task View grid (system/theme/tabbox, layout `zaldros-grid`).
    """
    before = out / f"{prefix}-before.ppm"
    held = out / f"{prefix}-held.ppm"
    after = out / f"{prefix}-after.ppm"
    qmp.screendump(before)
    started = time.monotonic()
    try:
        # `alt`, not `alt_l`: QKeyCode names the left Alt `alt`, and QEMU rejected every
        # `alt_l` event for six runs while this driver ignored the error reply (run #36).
        qmp.key_state(modifier, True)
        time.sleep(0.2)
        qmp.key_state("tab", True)
        qmp.key_state("tab", False)
        time.sleep(settle)
        qmp.screendump(held)
        qmp.key_state(modifier, False)
    except QMPError as exc:
        return {"status": "FAIL", "qmp_error": str(exc),
                "why": "the key was never delivered to the guest, so this says nothing about KWin"}
    time.sleep(settle)
    qmp.screendump(after)
    elapsed = round(time.monotonic() - started, 3)
    try:
        showed = changed_fraction(before, held)
        switched = changed_fraction(before, after)
    except Exception as exc:                                # noqa: BLE001 - reported, not hidden
        return {"status": "FAIL", "error": str(exc)}
    try:
        overlay = changed_fraction(held, after)
    except Exception as exc:                                # noqa: BLE001 - reported, not hidden
        return {"status": "FAIL", "error": str(exc)}
    verdict = alt_tab_verdict(showed, overlay, switched)
    verdict.update({"seconds": elapsed, "screenshot": after.name, "held_screenshot": held.name})
    return verdict


def alt_tab_verdict(showed, overlay, switched):
    """Turn three frame comparisons into claims that mean what they say.

    `showed` = before vs held, `overlay` = held vs after, `switched` = before vs after.

    The old version called `switcher_visible` true whenever the screen changed while Alt was held —
    but the window switch *itself* changes the screen while Alt is held, so the field was true even
    when no switcher had ever been drawn. iso run 33158172265 proved it: `alt_tab-held.png` and
    `alt_tab-after.png` were byte-identical (md5 a4880e3e48) and the report still said
    `switcher_visible: true`.

    An overlay that exists only while Alt is down must make the held frame differ from *both* the
    frame before it and the frame after release. If the held frame equals the release frame, the
    only honest thing to say is that no switcher was captured — and the window switch, which is
    the thing a user actually needs, is reported separately.
    """
    visible = overlay >= CHANGE_THRESHOLD and showed >= CHANGE_THRESHOLD
    return {
        # The step is about switching windows. A missing overlay is reported, not fatal.
        "status": "PASS" if switched >= CHANGE_THRESHOLD else "FAIL",
        "switched": switched >= CHANGE_THRESHOLD,
        "switched_fraction": switched,
        "switcher_visible": visible,
        "switcher_fraction": showed,
        "switcher_overlay_fraction": overlay,
        "held_equals_after": overlay < CHANGE_THRESHOLD,
        "note": ("measured with the guest's Dolphin window open. switcher_visible requires the "
                 "held frame to differ from both neighbours; when held == after, no switcher was "
                 "on screen while Alt was down and only the window change is proven."),
    }


# Four shortcuts the KWin script registers purely so this driver can ask the session one question
# it could never answer before: *which* key presses reach a global shortcut. Each one only prints
# a ZALDROS-PROBE line, and the guest's late report says which lines appeared. If none fire, the
# whole keyboard→kglobalaccel path is dead; if Meta+F9 fires and Alt+F9 does not, the Alt modifier
# is being eaten. Meta+Tab used to be pressed here; it now opens the alternative tabbox (the Task
# View grid), so the script's own cycle sits on Meta+F10 and that is what this presses.
PROBE_KEYS = {
    "meta_f9": ("meta_l", "f9"),
    "alt_f9": ("alt", "f9"),
    "ctrl_shift_f9": ("ctrl", "shift", "f9"),
    "meta_f10": ("meta_l", "f10"),
}


def probe_step(qmp):
    """Press each probe combination once and record that it was really sent."""
    sent = {}
    for name, keys in PROBE_KEYS.items():
        try:
            qmp.key(*keys)
            sent[name] = {"keys": list(keys), "sent": True}
        except QMPError as exc:
            sent[name] = {"keys": list(keys), "sent": False, "qmp_error": str(exc)}
        time.sleep(1.0)
    return {"status": "INFO", "pressed": sent,
            "note": "the verdict is in the guest's late report: each ZALDROS-PROBE line means "
                    "that combination reached a global shortcut"}


def second_window(serial_path):
    """Read the guest's ZALDROS-WINDOWS-READY line: does a second toplevel window really exist?

    Run #37 settled the Alt+Tab question the honest way. The key was delivered (no QMP errors),
    kglobalaccel fired our action (the guest logged `cycle reverse=false candidates=1`) and the
    KWin script then said `nothing to switch to` — because Dolphin was not open yet. The driver
    had been waiting for ZALDROS-GEOMETRY, which the *shell* prints seconds after login, long
    before the in-guest test launches an application. This marker is printed by that test itself,
    after KWin confirms the second window.
    """
    if not serial_path or not Path(serial_path).is_file():
        return None
    text = Path(serial_path).read_text(errors="replace")
    seen = None
    for line in text.splitlines():
        if "ZALDROS-WINDOWS-READY {" not in line:
            continue
        try:                                        # escaped copies inside embedded logs are skipped
            payload = json.loads(line.split("ZALDROS-WINDOWS-READY ", 1)[1])
        except Exception:
            continue
        if isinstance(payload, dict):
            seen = payload
    return seen


def wait_for_second_window(serial_path, timeout=180):
    """Alt+Tab with one window proves nothing, so the driver waits instead of measuring noise."""
    deadline = time.monotonic() + timeout
    waited = 0.0
    while time.monotonic() < deadline:
        found = second_window(serial_path)
        if found and found.get("ready"):
            found = dict(found)
            found["waited_seconds"] = round(waited, 1)
            return found
        time.sleep(2)
        waited += 2
    return second_window(serial_path)


def wait_for_marker(serial_path, marker, timeout=90):
    """Wait until a marker line appears on the serial log. Returns the seconds waited, or None.

    Used to keep the two halves of the test from stepping on each other: the guest moves,
    minimises and restores its own window, and an Alt+Tab measured in the middle of that would
    photograph somebody else's change.
    """
    if not serial_path:
        return None
    deadline = time.monotonic() + timeout
    started = time.monotonic()
    while time.monotonic() < deadline:
        try:
            if marker in Path(serial_path).read_text(errors="replace"):
                return round(time.monotonic() - started, 1)
        except OSError:
            pass
        time.sleep(2)
    return None


def hit_boxes(serial_path):
    """Read the last ZALDROS-GEOMETRY line the guest printed on the serial console."""
    if not serial_path or not Path(serial_path).is_file():
        return None
    text = Path(serial_path).read_text(errors="replace")
    hits = [line for line in text.splitlines() if "ZALDROS-GEOMETRY {" in line]
    if not hits:
        return None
    try:
        return json.loads(hits[-1].split("ZALDROS-GEOMETRY ", 1)[1])
    except Exception:
        return None


def wait_for_hit_boxes(serial_path, timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        boxes = hit_boxes(serial_path)
        if boxes and boxes.get("items"):
            return boxes
        time.sleep(1)
    return hit_boxes(serial_path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("qmp_socket")
    ap.add_argument("--out", default="results")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=800)
    ap.add_argument("--name", default="ui")
    ap.add_argument("--serial", help="serial log to read the guest's published hit boxes from")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    qmp = QMP(args.qmp_socket)

    steps = {
        "start_open": lambda: qmp.key("meta_l"),
        "start_close": lambda: qmp.key("esc"),
    }
    results = {name: timed_step(qmp, out, name, action) for name, action in steps.items()}

    # The taskbar group is centred and its width depends on the pinned applications, so the click
    # target comes from the guest itself. No coordinate is ever guessed: without the published
    # geometry the step reports BLOCKED and says why.
    start = (wait_for_hit_boxes(args.serial) or {}).get("items", {}).get("startButton")
    if start:
        results["taskbar_response"] = timed_step(
            qmp, out, "taskbar_response",
            lambda: qmp.click(start["x"], start["y"], args.width, args.height))
        results["taskbar_response"]["target"] = start
    else:
        results["taskbar_response"] = {
            "status": "BLOCKED",
            "why": "the guest did not publish /tmp/zaldros-ui-geometry.json, so the Start button "
                   "position on screen is unknown and clicking a guessed point proves nothing"}

    # Alt+Tab runs last, and only once the guest has reported a *second* window of its own.
    # Runs #27-#37 measured Alt+Tab while the shell was the only toplevel window: the shortcut
    # fires, the script finds one candidate and correctly does nothing, and the frame cannot
    # change — a FAIL for a feature that works. With no second window the honest answer is
    # BLOCKED, not FAIL.
    ready = wait_for_second_window(args.serial)
    if ready and ready.get("ready"):
        # ...and only once the guest has stopped moving that window around.
        waited = wait_for_marker(args.serial, "ZALDROS-UITEST {", timeout=90)
        results["alt_tab"] = alt_tab_step(qmp, out)
        results["alt_tab"]["second_window"] = ready
        results["alt_tab"]["guest_test_finished"] = waited is not None
        results["alt_tab"]["waited_for_guest_seconds"] = waited
        # Meta+Tab: the alternative tabbox in Task View proportions. Same three frames, so the
        # report can say whether it drew, not only whether a key was accepted.
        results["task_view"] = alt_tab_step(qmp, out, modifier="meta_l", prefix="task_view")
        results["shortcut_probes"] = probe_step(qmp)
    else:
        results["alt_tab"] = {
            "status": "BLOCKED",
            "second_window": ready,
            "why": "the guest never reported a second toplevel window (ZALDROS-WINDOWS-READY), and "
                   "Alt+Tab with one window cannot change the screen either way"}
        results["shortcut_probes"] = probe_step(qmp)
    results["qmp_errors"] = qmp.errors            # empty is the only acceptable value
    (out / f"{args.name}-host.json").write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
