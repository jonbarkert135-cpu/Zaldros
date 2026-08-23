"""Real system readouts for the tray and quick settings.

Rule for this file (spec PART 3 §25, PART 4): every function returns `None` when the value cannot be
measured on this machine. The UI must then show "нет данных" / a disabled control. We never invent a
battery level, a Wi-Fi signal or a volume percentage to make a screenshot look complete.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Reading:
    """A value plus how it was obtained. `available=False` means: show as unavailable."""

    available: bool
    value: int | None = None
    detail: str = ""
    source: str = ""


def _read_int(path: Path) -> int | None:
    try:
        return int(path.read_text().strip())
    except (OSError, ValueError):
        return None


def battery(sys_root: str = "/sys/class/power_supply") -> Reading:
    root = Path(sys_root)
    try:
        candidates = sorted(p for p in root.iterdir() if p.name.startswith("BAT"))
    except OSError:
        return Reading(False, detail="нет данных", source=sys_root)
    for path in candidates:
        percent = _read_int(path / "capacity")
        if percent is None:
            continue
        status = ""
        try:
            status = (path / "status").read_text().strip()
        except OSError:
            pass
        return Reading(True, percent, status, source=str(path))
    return Reading(False, detail="батарея не обнаружена", source=sys_root)


def backlight(sys_root: str = "/sys/class/backlight") -> Reading:
    root = Path(sys_root)
    try:
        devices = sorted(root.iterdir())
    except OSError:
        return Reading(False, detail="нет данных", source=sys_root)
    for device in devices:
        current, maximum = _read_int(device / "brightness"), _read_int(device / "max_brightness")
        if current is not None and maximum:
            return Reading(True, round(current / maximum * 100), source=str(device))
    return Reading(False, detail="регулировка недоступна", source=sys_root)


def network(sys_root: str = "/sys/class/net") -> Reading:
    """Reports the first non-loopback interface that is actually up."""
    root = Path(sys_root)
    try:
        interfaces = sorted(p for p in root.iterdir() if p.name != "lo")
    except OSError:
        return Reading(False, detail="нет данных", source=sys_root)
    for path in interfaces:
        try:
            state = (path / "operstate").read_text().strip()
        except OSError:
            continue
        if state == "up":
            wireless = (path / "wireless").exists()
            return Reading(True, None, f"{path.name} · {'Wi-Fi' if wireless else 'Ethernet'}",
                           source=str(path))
    return Reading(False, detail="нет подключения", source=sys_root)


def volume(runner=subprocess.run) -> Reading:
    """PipeWire (wpctl) or PulseAudio (pactl). Absent tooling means unavailable, not zero."""
    if shutil.which("wpctl"):
        try:
            out = runner(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"], capture_output=True,
                         text=True, timeout=2)
            token = out.stdout.split()[1]
            return Reading(True, round(float(token) * 100), source="wpctl")
        except (OSError, IndexError, ValueError, subprocess.SubprocessError):
            return Reading(False, detail="звук недоступен", source="wpctl")
    if shutil.which("pactl"):
        return Reading(False, detail="не опрошено", source="pactl")
    return Reading(False, detail="аудиосервер не найден", source="none")


def bluetooth(sys_root: str = "/sys/class/bluetooth") -> Reading:
    try:
        adapters = [p.name for p in Path(sys_root).iterdir()]
    except OSError:
        return Reading(False, detail="адаптер не найден", source=sys_root)
    if adapters:
        return Reading(True, None, adapters[0], source=sys_root)
    return Reading(False, detail="адаптер не найден", source=sys_root)


def user_name() -> str:
    return os.environ.get("USER") or os.environ.get("LOGNAME") or "пользователь"


def snapshot() -> dict[str, Reading]:
    return {"battery": battery(), "brightness": backlight(), "network": network(),
            "volume": volume(), "bluetooth": bluetooth()}
