"""Backend for the Bedrock Shell prototype.

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

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@dataclass(frozen=True)
class AppEntry:
    """A pinned or running application. `exec_name` is what we match against /proc comm."""

    name: str
    exec_name: str
    icon: str
    color: str


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
