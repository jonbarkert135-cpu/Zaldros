"""Backend for the Zaldros Shell prototype.

Everything exposed to QML here is either real system data (clock, locale, uptime, memory, running
processes read from /proc) or explicitly declared placeholder data (the pinned application list, which
comes from a JSON file). No fake hardware state, no fake battery, no fake network strength — spec
PART 3 §25 forbids inventing system information for a nicer screenshot.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

def _data_dir() -> Path:
    """Find the shell's data tree (`pinned.json`).

    Run #24: the ISO copied `zaldros_shell/`, `qml/` and `assets/` into /opt/zaldros but never
    `data/`, so the shell died at startup with FileNotFoundError on /opt/zaldros/data/pinned.json
    and every variant booted to a black screen. The copy is fixed in build-iso.sh; this resolver
    also accepts the repo layout, the flat layout and an explicit override, and never invents
    data when the file is absent.
    """
    candidates = [Path(os.environ["ZALDROS_DATA"])] if os.environ.get("ZALDROS_DATA") else []
    here = Path(__file__).resolve()
    candidates += [here.parents[1] / "data", Path("/opt/zaldros/data")]
    for path in candidates:
        if (path / "pinned.json").is_file():
            return path
    return candidates[-1]  # keep a stable path: a missing file must fail loudly, not silently


DATA_DIR = _data_dir()


@dataclass(frozen=True)
class AppEntry:
    """A pinned or running application. `exec_name` is what we match against /proc comm."""

    name: str
    exec_name: str
    icon: str
    color: str
    taskbar: bool = False   # shown on the bar itself; the others are Start-only pins


def load_pinned(path: Path | None = None) -> list[AppEntry]:
    source = path or DATA_DIR / "pinned.json"
    with open(source, encoding="utf-8") as handle:
        raw = json.load(handle)
    return [AppEntry(**entry) for entry in raw["pinned"]]


def read_running_commands(proc_root: str = "/proc") -> set[str]:
    """Real process names from /proc/<pid>/comm. Empty set if /proc is not readable."""
    names: set[str] = set()
    try:
        pids = [name for name in os.listdir(proc_root) if name.isdigit()]
    except OSError:
        return names
    for pid in pids:
        try:
            with open(os.path.join(proc_root, pid, "comm"), encoding="utf-8") as handle:
                names.add(handle.read().strip())
        except OSError:
            continue
    return names


def format_clock(moment: time.struct_time, locale: str = "ru") -> tuple[str, str]:
    """Taskbar clock. Windows 11 shows time above date, right-aligned, locale-formatted."""
    if locale.startswith("ru"):
        return time.strftime("%H:%M", moment), time.strftime("%d.%m.%Y", moment)
    if locale.startswith("en_US") or locale == "en":
        return time.strftime("%I:%M %p", moment).lstrip("0"), time.strftime("%m/%d/%Y", moment)
    return time.strftime("%H:%M", moment), time.strftime("%d/%m/%Y", moment)


def cpu_times(proc_root: str = "/proc") -> tuple[int, int] | None:
    """(busy, total) jiffies from /proc/stat. None when unreadable — never guessed.

    A single reading says nothing about load; the caller keeps the previous one and reports the
    difference, which is what every honest CPU meter does.
    """
    try:
        with open(os.path.join(proc_root, "stat"), encoding="utf-8") as handle:
            first = handle.readline()
    except OSError:
        return None
    parts = first.split()
    if not parts or parts[0] != "cpu":
        return None
    try:
        values = [int(value) for value in parts[1:]]
    except ValueError:
        return None
    if len(values) < 4:
        return None
    idle = values[3] + (values[4] if len(values) > 4 else 0)
    total = sum(values)
    return total - idle, total


def cpu_percent(previous, current) -> int | None:
    """Load between two `cpu_times` readings. None until there are two of them."""
    if not previous or not current:
        return None
    busy = current[0] - previous[0]
    total = current[1] - previous[1]
    if total <= 0:
        return None
    return max(0, min(100, round(busy / total * 100)))


def memory_percent(proc_root: str = "/proc") -> int | None:
    """Real memory pressure for the Start menu footer. None when unreadable — never guessed."""
    try:
        with open(os.path.join(proc_root, "meminfo"), encoding="utf-8") as handle:
            values = {}
            for line in handle:
                key, _, rest = line.partition(":")
                parts = rest.split()
                if parts and parts[0].isdigit():
                    values[key] = int(parts[0])
    except OSError:
        return None
    total, available = values.get("MemTotal"), values.get("MemAvailable")
    if not total or available is None:
        return None
    return round((total - available) / total * 100)
