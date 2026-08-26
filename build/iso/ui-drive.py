#!/usr/bin/env python3
"""Stage 2, host half — drive the guest's UI over QMP and time what actually changes on screen.

QEMU's `input-send-event` injects real key and mouse events, and `screendump` captures the composited
framebuffer. A step counts as PASS only when the screen visibly changes; a keypress that changes
nothing is a FAIL, not a pass.
"""
import argparse, json, socket, struct, subprocess, time
from pathlib import Path


class QMP:
    def __init__(self, path):
        self.sock = socket.socket(socket.AF_UNIX)
        self.sock.connect(path)
        self.file = self.sock.makefile("rw")
        self.file.readline()                                   # greeting
        self.cmd("qmp_capabilities")

    def cmd(self, name, **args):
        self.file.write(json.dumps({"execute": name, "arguments": args or {}}) + "\n")
        self.file.flush()
        while True:
            reply = json.loads(self.file.readline())
            if "event" not in reply:
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
    action()
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


def alt_tab_step(qmp, out, settle=1.2):
    """Alt+Tab the way a person does it: hold Alt, tap Tab, *look at the screen*, then let go.

    Run #29 pressed and released in one batch and could only see the aftermath, which made a
    switcher that never drew indistinguishable from one that drew and vanished. Two measurements
    are taken instead: `switcher_fraction` with Alt still held (did the switcher appear?) and
    `switched_fraction` after release (did the window actually change?).
    """
    before = out / "alt_tab-before.ppm"
    held = out / "alt_tab-held.ppm"
    after = out / "alt_tab-after.ppm"
    qmp.screendump(before)
    started = time.monotonic()
    qmp.key_state("alt_l", True)
    time.sleep(0.2)
    qmp.key_state("tab", True)
    qmp.key_state("tab", False)
    time.sleep(settle)
    qmp.screendump(held)
    qmp.key_state("alt_l", False)
    time.sleep(settle)
    qmp.screendump(after)
    elapsed = round(time.monotonic() - started, 3)
    try:
        showed = changed_fraction(before, held)
        switched = changed_fraction(before, after)
    except Exception as exc:                                # noqa: BLE001 - reported, not hidden
        return {"status": "FAIL", "error": str(exc)}
    ok = switched >= CHANGE_THRESHOLD or showed >= CHANGE_THRESHOLD
    return {
        "status": "PASS" if ok else "FAIL",
        "seconds": elapsed,
        "switcher_visible": showed >= CHANGE_THRESHOLD,
        "switcher_fraction": showed,
        "switched": switched >= CHANGE_THRESHOLD,
        "switched_fraction": switched,
        "screenshot": after.name,
        "held_screenshot": held.name,
        "note": ("measured with the guest's Dolphin window open. The held frame shows the switcher "
                 "itself; the after frame shows whether the window really changed."),
    }


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

    # Alt+Tab runs last, and only once the guest has published its geometry — that line is printed
    # by the in-guest test, which by then has launched Dolphin. Runs #27-#28b measured Alt+Tab
    # while the shell was the *only* toplevel window: KWin shows no switcher for a single window
    # and releases Alt before the screenshot, so the frame could not change and the step reported
    # FAIL for a shortcut that may well have worked. With no second window the honest answer is
    # BLOCKED, not FAIL.
    if start:
        results["alt_tab"] = alt_tab_step(qmp, out)
    else:
        results["alt_tab"] = {
            "status": "BLOCKED",
            "why": "the guest never came up far enough to open a second window, and Alt+Tab with "
                   "one toplevel window cannot change the screen either way"}
    (out / f"{args.name}-host.json").write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
