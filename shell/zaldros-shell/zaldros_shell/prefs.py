"""User preferences that actually change the desktop and survive a reboot.

Until now every switch in Settings was a painted rectangle: the tree carried a hard-coded
`toggle=True/False` and clicking it changed nothing. A switch that does not switch is worse than
no switch, so the ones we can honestly implement are backed by this store and the rest keep
showing their real, read-only state (Bluetooth presence, Wi-Fi, and so on).

The file is a plain `key=value` text file under $XDG_CONFIG_HOME/zaldros/settings.conf, written
atomically so a power cut cannot leave half a line behind. Unknown keys in the file are kept on
write, so a newer session's settings are not destroyed by an older one.
"""

from __future__ import annotations

import os
from pathlib import Path

# Only switches we can really honour belong here. Each entry: key -> (default, what it changes).
DEFAULTS: dict[str, bool] = {
    "taskbar.search": True,        # the search field on the taskbar
    "taskbar.widgets": True,       # the weather/widgets button on the left
    "taskbar.taskview": True,      # the task view button
    "taskbar.clock": True,         # the clock in the tray
    "visual.transparency": True,   # translucent panels and menus
    "visual.animations": True,     # transitions in the shell
    "start.recent": True,          # the "Рекомендуем" section in the Start panel
}


def config_path(home: Path | None = None) -> Path:
    """$XDG_CONFIG_HOME/zaldros/settings.conf, with the spec's fallback to ~/.config.

    An explicit `home` wins over the environment: tests must never write to the real home
    directory, and files.py learned that lesson the hard way.
    """
    if home is not None:
        return Path(home) / ".config" / "zaldros" / "settings.conf"
    base = os.environ.get("XDG_CONFIG_HOME") or ""
    root = Path(base) if base else Path.home() / ".config"
    return root / "zaldros" / "settings.conf"


def _parse(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip()
    return values


def read_raw(home: Path | None = None) -> dict[str, str]:
    path = config_path(home)
    try:
        return _parse(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        return {}


def load(home: Path | None = None) -> dict[str, bool]:
    """Every known switch with its effective value: the file when it says something valid,
    the default otherwise. A corrupt line is ignored, never guessed at."""
    raw = read_raw(home)
    out = dict(DEFAULTS)
    for key in DEFAULTS:
        value = raw.get(key, "").lower()
        if value in ("true", "1", "yes", "on"):
            out[key] = True
        elif value in ("false", "0", "no", "off"):
            out[key] = False
    return out


def save(values: dict[str, bool], home: Path | None = None) -> Path:
    """Write the switches, keeping any key we do not know about."""
    path = config_path(home)
    path.parent.mkdir(parents=True, exist_ok=True)
    merged = read_raw(home)
    for key, value in values.items():
        merged[key] = "true" if value else "false"
    body = "".join(f"{key}={merged[key]}\n" for key in sorted(merged))
    tmp = path.with_suffix(".conf.tmp")
    tmp.write_text("# Zaldros settings. Written by the shell; safe to edit by hand.\n" + body,
                   encoding="utf-8")
    os.replace(tmp, path)
    return path


def set_value(key: str, value: bool, home: Path | None = None) -> bool:
    """Set one switch. Returns False for a key we do not implement, instead of silently
    inventing a preference that nothing reads."""
    if key not in DEFAULTS:
        return False
    current = load(home)
    current[key] = bool(value)
    save(current, home)
    return True
