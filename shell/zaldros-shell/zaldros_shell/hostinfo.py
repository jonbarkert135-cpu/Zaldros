"""Machine facts, formatted for the Settings application.

The *measuring* moved to `zaldros_backend.hardware`, which is the one place that reads /proc,
/sys and DMI; this file is what turns those numbers into the strings Settings shows — Russian
decimal commas, «ГиБ», «2 ч 15 мин», and a dash for anything the machine did not report.

Keeping the split matters: the backend must stay usable from a tool or a test that wants bytes,
and Settings must stay free to change wording without touching a reader.
"""

from __future__ import annotations

import os
import platform
import socket
import time
from pathlib import Path

from zaldros_backend import hardware


def _first_line(path: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace").splitlines()[0].strip()
    except (OSError, IndexError):
        return ""


def os_name() -> str:
    return hardware.os_name()


def _read_lines(path: str) -> list[str]:
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []


def cpu_model() -> str:
    return hardware.cpu_model()


def cpu_cores() -> int:
    return hardware.cpu_cores()


# A filesystem is allowed to report a size; it is not allowed to report a size no disk has. Some
# overlay and virtual filesystems answer with a sentinel (we have seen 8589934591 GiB, which is
# 2**63 blocks). Above this ceiling the reading is treated as no reading at all.
IMPLAUSIBLE_BYTES = hardware.IMPLAUSIBLE_BYTES  # 1 PiB


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
    return hardware.meminfo_bytes()


def memory_total_bytes() -> int:
    return _meminfo_bytes().get("MemTotal", 0)


def memory_used_bytes() -> int:
    values = _meminfo_bytes()
    if "MemTotal" in values and "MemAvailable" in values:
        return values["MemTotal"] - values["MemAvailable"]
    return 0


def disk_usage(path: str = "/") -> tuple[int, int]:
    """(used bytes, total bytes), or (0, 0) when the filesystem reports a size no real disk has."""
    return hardware.disk_usage(path)


def uptime_seconds() -> int:
    return hardware.uptime_seconds()


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


def virtualization() -> str:
    """"qemu", "kvm", "vmware"... or "" on real hardware. Settings shows it so a screenshot from
    a virtual machine cannot be mistaken for one from a laptop."""
    return hardware.virtualization()


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
