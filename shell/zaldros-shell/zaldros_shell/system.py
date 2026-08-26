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


# Windows 11 shows the layout as a three-letter badge in the UI language: РУС, ENG, УКР. Layouts
# we have no name for keep their own code rather than getting an invented translation.
LAYOUT_BADGES = {"ru": "РУС", "us": "ENG", "en": "ENG", "gb": "ENG", "ua": "УКР", "uk": "УКР",
                 "de": "DEU", "fr": "FRA", "es": "ESP", "it": "ITA", "pl": "POL", "he": "ИВР",
                 "tr": "TUR", "pt": "POR", "cz": "ČES", "kk": "ҚАЗ"}


def layout_badge(code: str) -> str:
    """Tray badge for a keyboard layout code such as "ru", "us" or "ru,us"."""
    first = code.split(",")[0].strip().lower()
    return LAYOUT_BADGES.get(first, first.upper()[:3])


def keyboard_layout(runner=subprocess.run) -> Reading:
    """Active keyboard layout, read from the session. Windows shows it in the tray, so we do too —
    but only when something really reports one."""
    if shutil.which("localectl"):
        try:
            result = runner(["localectl", "status"], capture_output=True, text=True, timeout=2)
        except (OSError, subprocess.SubprocessError):
            result = None
        if result is not None and result.returncode == 0:
            for line in result.stdout.splitlines():
                key, _, value = line.partition(":")
                if key.strip() not in ("X11 Layout", "VC Keymap"):
                    continue
                code = value.strip()
                # localectl answers "(unset)" on an image where nothing configured a keymap. Run
                # #29 shipped that straight to the tray, which read "(UN": a real value in the
                # protocol, no value to a human.
                if code.lower() in ("", "n/a", "unset", "(unset)"):
                    continue
                return Reading(True, None, layout_badge(code), source="localectl")
    language = os.environ.get("LANG", "").split(".")[0].split("_")[0]
    if len(language) == 2 and language.isalpha():
        return Reading(True, None, layout_badge(language), source="LANG")
    return Reading(False, detail="раскладка не определена", source="localectl")


def user_name() -> str:
    return os.environ.get("USER") or os.environ.get("LOGNAME") or "пользователь"


def snapshot() -> dict[str, Reading]:
    return {"battery": battery(), "brightness": backlight(), "network": network(),
            "volume": volume(), "bluetooth": bluetooth(), "keyboard": keyboard_layout()}
