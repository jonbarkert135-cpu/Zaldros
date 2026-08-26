"""Real facts about this machine, for the Settings application.

Every reading comes from the running system (/proc, /etc/os-release, os.statvfs). A reading that
cannot be taken returns an empty string and Settings shows a dash, never a plausible-looking
placeholder.
"""

from __future__ import annotations

import os
import platform
import shutil
import socket
import time
from pathlib import Path


def _first_line(path: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace").splitlines()[0].strip()
    except (OSError, IndexError):
        return ""


def os_name() -> str:
    for line in _read_lines("/etc/os-release"):
        key, _, value = line.partition("=")
        if key == "PRETTY_NAME":
            return value.strip().strip('"')
    return ""


def _read_lines(path: str) -> list[str]:
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []


def cpu_model() -> str:
    for line in _read_lines("/proc/cpuinfo"):
        key, _, value = line.partition(":")
        if key.strip() in ("model name", "Model", "Processor"):
            return value.strip()
    return platform.processor() or ""


def cpu_cores() -> int:
    return os.cpu_count() or 0


# A filesystem is allowed to report a size; it is not allowed to report a size no disk has. Some
# overlay and virtual filesystems answer with a sentinel (we have seen 8589934591 GiB, which is
# 2**63 blocks). Above this ceiling the reading is treated as no reading at all.
IMPLAUSIBLE_BYTES = 1024 ** 5  # 1 PiB


def format_bytes(size: int) -> str:
    """Human size in the units Windows uses for the same rows: МиБ under a gigabyte, ТиБ over a
    thousand. Returns "" for a size we do not have, so Settings can show a dash."""
    if size <= 0:
        return ""
    if size >= IMPLAUSIBLE_BYTES:
        return ""
    if size < 1024 ** 3:
        return f"{size / 1024 ** 2:.0f} МиБ"
    if size < 1024 ** 4:
        gib = size / 1024 ** 3
        return _ru(f"{gib:.1f} ГиБ" if gib < 100 else f"{gib:.0f} ГиБ")
    return _ru(f"{size / 1024 ** 4:.1f} ТиБ")


def _ru(text: str) -> str:
    """Russian writes 8,0 — not 8.0. The interface is Russian, so the numbers are too."""
    return text.replace(".", ",")


def _meminfo_bytes() -> dict[str, int]:
    values = {}
    for line in _read_lines("/proc/meminfo"):
        key, _, rest = line.partition(":")
        parts = rest.split()
        if parts and parts[0].isdigit():
            values[key] = int(parts[0]) * 1024  # /proc/meminfo is in kB
    return values


def memory_total_bytes() -> int:
    return _meminfo_bytes().get("MemTotal", 0)


def memory_used_bytes() -> int:
    values = _meminfo_bytes()
    if "MemTotal" in values and "MemAvailable" in values:
        return values["MemTotal"] - values["MemAvailable"]
    return 0


def disk_usage(path: str = "/") -> tuple[int, int]:
    """(used bytes, total bytes) for the filesystem holding `path`; (0, 0) when unavailable or
    when the filesystem reports a size no real disk has."""
    try:
        usage = shutil.disk_usage(path)
    except OSError:
        return (0, 0)
    if usage.total <= 0 or usage.total >= IMPLAUSIBLE_BYTES:
        return (0, 0)
    return (usage.used, usage.total)


def uptime_seconds() -> int:
    first = _first_line("/proc/uptime")
    try:
        return int(float(first.split()[0]))
    except (ValueError, IndexError):
        return 0


def format_uptime(seconds: int) -> str:
    if seconds <= 0:
        return ""
    hours, rest = divmod(seconds, 3600)
    minutes = rest // 60
    if hours:
        return f"{hours} ч {minutes} мин"
    return f"{minutes} мин"


def device_name() -> str:
    return socket.gethostname()


def kernel() -> str:
    return f"{platform.system()} {platform.release()}"


def session_type() -> str:
    return os.environ.get("XDG_SESSION_TYPE") or ("wayland" if os.environ.get("WAYLAND_DISPLAY") else "")


def local_time() -> str:
    return time.strftime("%d.%m.%Y %H:%M")


def timezone() -> str:
    return time.tzname[0] if time.tzname else ""


def snapshot() -> dict[str, str]:
    """Everything Settings needs, already formatted for display."""
    used_bytes, total_bytes = disk_usage()
    memory_total = memory_total_bytes()
    memory_used = memory_used_bytes()
    return {
        "deviceName": device_name(),
        "osName": os_name(),
        "kernel": kernel(),
        "architecture": platform.machine(),
        "cpuModel": cpu_model(),
        "cpuCores": str(cpu_cores()) if cpu_cores() else "",
        "memoryTotal": format_bytes(memory_total),
        "memoryUsed": format_bytes(memory_used),
        "diskUsed": format_bytes(used_bytes) if total_bytes else "",
        "diskTotal": format_bytes(total_bytes),
        "uptime": format_uptime(uptime_seconds()),
        "sessionType": session_type(),
        "localTime": local_time(),
        "timezone": timezone(),
        "python": platform.python_version(),
    }
