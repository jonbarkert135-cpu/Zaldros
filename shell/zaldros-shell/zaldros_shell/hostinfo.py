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


def memory_total_mib() -> int:
    for line in _read_lines("/proc/meminfo"):
        if line.startswith("MemTotal:"):
            return int(line.split()[1]) // 1024
    return 0


def memory_used_mib() -> int:
    values = {}
    for line in _read_lines("/proc/meminfo"):
        key, _, rest = line.partition(":")
        parts = rest.split()
        if parts and parts[0].isdigit():
            values[key] = int(parts[0]) // 1024
    if "MemTotal" in values and "MemAvailable" in values:
        return values["MemTotal"] - values["MemAvailable"]
    return 0


def disk_usage(path: str = "/") -> tuple[int, int]:
    """(used GiB, total GiB) for the filesystem holding `path`; (0, 0) when unavailable."""
    try:
        usage = shutil.disk_usage(path)
    except OSError:
        return (0, 0)
    return (usage.used // 1024 ** 3, usage.total // 1024 ** 3)


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
    used_gib, total_gib = disk_usage()
    memory_total = memory_total_mib()
    memory_used = memory_used_mib()
    return {
        "deviceName": device_name(),
        "osName": os_name(),
        "kernel": kernel(),
        "architecture": platform.machine(),
        "cpuModel": cpu_model(),
        "cpuCores": str(cpu_cores()) if cpu_cores() else "",
        "memoryTotal": f"{memory_total / 1024:.1f} ГиБ" if memory_total else "",
        "memoryUsed": f"{memory_used / 1024:.1f} ГиБ" if memory_used else "",
        "diskUsed": f"{used_gib} ГиБ" if total_gib else "",
        "diskTotal": f"{total_gib} ГиБ" if total_gib else "",
        "uptime": format_uptime(uptime_seconds()),
        "sessionType": session_type(),
        "localTime": local_time(),
        "timezone": timezone(),
        "python": platform.python_version(),
    }
