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


def ppm_signature(path):
    """Cheap change detector: mean pixel value of a PPM, no image libraries needed."""
    data = Path(path).read_bytes()
    parts = data.split(b"\n", 3)
    pixels = parts[3] if len(parts) > 3 else b""
    return round(sum(pixels[::997]) / max(len(pixels[::997]), 1), 3)


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
        changed = ppm_signature(before) != ppm_signature(after)
    except Exception as exc:
        return {"status": "FAIL", "error": str(exc)}
    return {"status": "PASS" if changed else "FAIL", "seconds": elapsed,
            "screen_changed": changed, "screenshot": after.name}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("qmp_socket")
    ap.add_argument("--out", default="results")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=800)
    ap.add_argument("--name", default="ui")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    qmp = QMP(args.qmp_socket)

    steps = {
        "start_open": lambda: qmp.key("meta_l"),
        "start_close": lambda: qmp.key("esc"),
        "alt_tab": lambda: qmp.key("alt_l", "tab"),
        "taskbar_response": lambda: qmp.click(24, args.height - 24, args.width, args.height),
    }
    results = {name: timed_step(qmp, out, name, action) for name, action in steps.items()}
    (out / f"{args.name}-host.json").write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
