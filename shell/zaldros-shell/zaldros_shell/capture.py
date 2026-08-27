"""Screen capture — the machinery behind Win+G.

No Qt in here, like clipboard.py and files.py: where the files go, what they are called, which
tool on this system can actually do the job, and the exact command line that will be run. All of
it is testable without a display, and `model.GameBarModel` is the thin Qt layer on top.

The rule this file exists to keep: **a button that cannot do its job says so.** Windows' game bar
is full of tiles that quietly do nothing on a machine without the right service; here every
capability is resolved to a real executable found in `PATH`, and when nothing can do it the UI
gets a sentence explaining what is missing instead of a dead button.

Where captures go follows the XDG user directories (`user-dirs.dirs`), which is the Linux
equivalent of Windows' `Videos\\Captures`:

* screenshots → `<PICTURES>/Zaldros/Снимки экрана`
* recordings  → `<VIDEOS>/Zaldros/Записи`
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

SCREENSHOT_SUBDIR = ("Снимки экрана",)
RECORDING_SUBDIR = ("Записи",)
STAMP = "%Y-%m-%d %H-%M-%S"


# --- where the files live ------------------------------------------------------------------
def _xdg_user_dir(name: str, fallback: str, home: Path | None = None) -> Path:
    """Read one entry of ~/.config/user-dirs.dirs. No xdg-user-dir binary is required."""
    root = Path(home) if home else Path.home()
    env = os.environ.get(f"XDG_{name}_DIR")
    if env and not home:
        return Path(os.path.expandvars(env)).expanduser()
    config = os.environ.get("XDG_CONFIG_HOME") if not home else None
    conf_dir = Path(config) if config else root / ".config"
    try:
        text = (conf_dir / "user-dirs.dirs").read_text(encoding="utf-8")
    except OSError:
        text = ""
    found = re.search(rf'^XDG_{name}_DIR="(.*)"', text, re.M)
    if found:
        value = found.group(1).replace("$HOME", str(root))
        return Path(value)
    return root / fallback


def screenshots_dir(home: Path | None = None) -> Path:
    return _xdg_user_dir("PICTURES", "Pictures", home).joinpath("Zaldros", *SCREENSHOT_SUBDIR)


def recordings_dir(home: Path | None = None) -> Path:
    return _xdg_user_dir("VIDEOS", "Videos", home).joinpath("Zaldros", *RECORDING_SUBDIR)


def screenshot_name(when: float | None = None) -> str:
    return time.strftime(f"Снимок {STAMP}.png", time.localtime(when))


def recording_name(when: float | None = None) -> str:
    return time.strftime(f"Запись {STAMP}.mp4", time.localtime(when))


# --- what this machine can actually do -----------------------------------------------------
@dataclass(frozen=True)
class Tool:
    """One way of doing the job, and the check that says whether it is really here."""

    name: str
    binary: str
    why: str


# Ordered by preference. Spectacle is KDE's own and speaks to KWin directly; the portal is the
# desktop-neutral fallback; grim covers wlroots sessions where somebody runs our shell.
SCREENSHOT_TOOLS = (
    Tool("spectacle", "spectacle", "KDE's own grabber, talks to KWin over D-Bus"),
    Tool("portal", "gdbus", "xdg-desktop-portal Screenshot, the desktop-neutral route"),
    Tool("grim", "grim", "wlroots grabber, for sessions without KWin"),
)
RECORDING_TOOLS = (
    Tool("ffmpeg", "ffmpeg", "ffmpeg's pipewiregrab source, fed by the portal's ScreenCast"),
    Tool("wf-recorder", "wf-recorder", "wlroots recorder, for sessions without KWin"),
)


def which(binary: str) -> str | None:
    return shutil.which(binary)


def pick(tools=SCREENSHOT_TOOLS) -> Tool | None:
    for tool in tools:
        if which(tool.binary):
            return tool
    return None


def ffmpeg_has_pipewiregrab(run=subprocess.run) -> bool:
    """ffmpeg only grew the `pipewiregrab` filter in 7.0; asking is cheaper than assuming."""
    if not which("ffmpeg"):
        return False
    try:
        out = run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True,
                  timeout=10)
    except Exception:                                 # noqa: BLE001 — a missing tool is data
        return False
    return "pipewiregrab" in (out.stdout or "")


def missing_reason(kind: str) -> str:
    """One sentence for the UI when a capability is not available. Never a shrug."""
    if kind == "screenshot":
        names = ", ".join(t.binary for t in SCREENSHOT_TOOLS)
        return f"Снимок экрана недоступен: в системе нет ни одного из {names}"
    names = ", ".join(t.binary for t in RECORDING_TOOLS)
    return (f"Запись недоступна: нужен {names} и портал захвата экрана "
            f"(xdg-desktop-portal), их здесь нет")


# --- the commands --------------------------------------------------------------------------
def screenshot_command(target: Path, tool: Tool | None = None) -> list[str] | None:
    """The argv that writes a screenshot to `target`, or None if nothing here can do it."""
    tool = tool or pick(SCREENSHOT_TOOLS)
    if tool is None:
        return None
    if tool.name == "spectacle":
        # -b background, -n no notification, -f full screen, -o output file
        return ["spectacle", "-b", "-n", "-f", "-o", str(target)]
    if tool.name == "grim":
        return ["grim", str(target)]
    # The portal writes into its own directory and answers with a URI; the caller moves the file.
    return ["gdbus", "call", "--session", "--dest", "org.freedesktop.portal.Desktop",
            "--object-path", "/org/freedesktop/portal/desktop",
            "--method", "org.freedesktop.portal.Screenshot.Screenshot",
            "", "{'interactive': <false>}"]


def recording_command(target: Path, node: int | None = None, fd: int | None = None,
                      with_microphone: bool = False, tool: Tool | None = None) -> list[str] | None:
    """The argv that records the screen into `target`.

    With ffmpeg the frames come from the PipeWire node the portal handed us (`node`/`fd` from
    `portal.screencast_session`); without a node there is nothing to read, so this returns None
    rather than a command that would record a black rectangle.
    """
    tool = tool or pick(RECORDING_TOOLS)
    if tool is None:
        return None
    if tool.name == "wf-recorder":
        cmd = ["wf-recorder", "-f", str(target)]
        if with_microphone:
            cmd += ["--audio"]
        return cmd
    if node is None:
        return None
    source = f"pipewiregrab=node={node}"
    if fd is not None:
        source += f":fd={fd}"
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", source]
    if with_microphone:
        cmd += ["-f", "pulse", "-i", "default", "-c:a", "aac", "-b:a", "128k"]
    cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
            "-y", str(target)]
    return cmd


def elapsed_text(seconds: float) -> str:
    """The timer on the recording pill: m:ss under an hour, h:mm:ss above it."""
    seconds = max(0, int(seconds))
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"
