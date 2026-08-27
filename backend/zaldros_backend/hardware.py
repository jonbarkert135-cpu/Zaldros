"""Hardware detection: the kernel's own answer, not a database lookup.

Everything here comes from /proc, /sys and DMI. No `lshw`, no `hwinfo`, no PCI-ID download: the
files are already on the machine, reading them costs microseconds, and they cannot be out of date.
What the kernel does not say, Settings shows as a dash.

This is also where the CPU and memory meters live, because a meter is a hardware reading and
because it keeps the difference-of-two-samples rule in one place: a single /proc/stat reading says
nothing about load, so `cpu_percent` needs two and returns None until it has them.
"""

from __future__ import annotations

import os
import platform
import socket
import time
from pathlib import Path
from typing import Any

DMI = "/sys/class/dmi/id"
IMPLAUSIBLE_BYTES = 1024 ** 5      # 1 PiB: overlay filesystems report sentinels, disks do not

# PCI vendor ids, for naming a GPU without a 2 MB ids file.
PCI_VENDORS = {"0x8086": "Intel", "0x10de": "NVIDIA", "0x1002": "AMD", "0x1af4": "Red Hat",
               "0x1234": "QEMU", "0x15ad": "VMware", "0x1414": "Microsoft", "0x1b36": "QEMU"}


def _text(path: str | Path) -> str:
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""


def _lines(path: str | Path) -> list[str]:
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []


# -- processor -------------------------------------------------------------------------------
def cpu_model(proc_root: str = "/proc") -> str:
    for line in _lines(os.path.join(proc_root, "cpuinfo")):
        key, _, value = line.partition(":")
        if key.strip() in ("model name", "Model", "Processor"):
            return value.strip()
    return platform.processor() or ""


def cpu_cores() -> int:
    return os.cpu_count() or 0


def cpu_times(proc_root: str = "/proc") -> tuple[int, int] | None:
    """(busy, total) jiffies from /proc/stat. None when unreadable — never guessed."""
    lines = _lines(os.path.join(proc_root, "stat"))
    if not lines:
        return None
    parts = lines[0].split()
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


def cpu_percent(previous: tuple[int, int] | None,
                current: tuple[int, int] | None) -> int | None:
    """Load between two `cpu_times` readings. None until there are two of them."""
    if not previous or not current:
        return None
    busy = current[0] - previous[0]
    total = current[1] - previous[1]
    if total <= 0:
        return None
    return max(0, min(100, round(busy / total * 100)))


def temperature(sys_root: str = "/sys/class/thermal") -> int | None:
    """The warmest zone, in whole degrees. None when the machine exposes no thermal zone."""
    best: int | None = None
    try:
        zones = sorted(Path(sys_root).glob("thermal_zone*"))
    except OSError:
        return None
    for zone in zones:
        raw = _text(zone / "temp")
        if not raw.lstrip("-").isdigit():
            continue
        celsius = int(raw) // 1000
        if -50 < celsius < 150 and (best is None or celsius > best):
            best = celsius
    return best


# -- memory ----------------------------------------------------------------------------------
def meminfo_bytes(proc_root: str = "/proc") -> dict[str, int]:
    values: dict[str, int] = {}
    for line in _lines(os.path.join(proc_root, "meminfo")):
        key, _, rest = line.partition(":")
        parts = rest.split()
        if parts and parts[0].isdigit():
            values[key] = int(parts[0]) * 1024     # /proc/meminfo counts kB
    return values


def memory_percent(proc_root: str = "/proc") -> int | None:
    values = meminfo_bytes(proc_root)
    total, available = values.get("MemTotal"), values.get("MemAvailable")
    if not total or available is None:
        return None
    return round((total - available) / total * 100)


def swap_percent(proc_root: str = "/proc") -> int | None:
    values = meminfo_bytes(proc_root)
    total, free = values.get("SwapTotal"), values.get("SwapFree")
    if not total or free is None:
        return None
    return round((total - free) / total * 100)


# -- machine ---------------------------------------------------------------------------------
def os_name() -> str:
    for line in _lines("/etc/os-release"):
        key, _, value = line.partition("=")
        if key == "PRETTY_NAME":
            return value.strip().strip('"')
    return ""


def firmware(dmi_root: str = DMI) -> dict[str, str]:
    """Vendor, model and BIOS, the way Windows's «Сведения о системе» lists them.

    DMI is world-readable except for the serial numbers, which need root; we do not ask for them,
    because the shell has no reason to know a machine's serial.
    """
    root = Path(dmi_root)
    return {name: _text(root / source) for name, source in (
        ("vendor", "sys_vendor"), ("product", "product_name"), ("version", "product_version"),
        ("family", "product_family"), ("board", "board_name"),
        ("bios_vendor", "bios_vendor"), ("bios_version", "bios_version"),
        ("bios_date", "bios_date"), ("chassis", "chassis_type"))}


def graphics(drm_root: str = "/sys/class/drm") -> list[str]:
    """The GPUs the kernel bound a driver to, named by vendor and driver."""
    out: list[str] = []
    try:
        cards = sorted(path for path in Path(drm_root).glob("card[0-9]*")
                       if "-" not in path.name)
    except OSError:
        return out
    for card in cards:
        device = card / "device"
        vendor = PCI_VENDORS.get(_text(device / "vendor"), _text(device / "vendor"))
        driver = os.path.basename(os.path.realpath(device / "driver")) if (
            device / "driver").exists() else ""
        label = " ".join(part for part in (vendor, driver) if part)
        if label and label not in out:
            out.append(label)
    return out


def virtualization() -> str:
    """"kvm", "qemu", "vmware", "microsoft"... or "" on real hardware.

    Read from DMI rather than by running systemd-detect-virt: the ISO boot test runs in QEMU and
    needs this to be true without a helper binary being installed.
    """
    vendor = (_text(f"{DMI}/sys_vendor") + " " + _text(f"{DMI}/product_name")).casefold()
    for needle, name in (("qemu", "qemu"), ("kvm", "kvm"), ("vmware", "vmware"),
                         ("virtualbox", "virtualbox"), ("microsoft", "hyper-v"),
                         ("bochs", "qemu"), ("xen", "xen"), ("parallels", "parallels")):
        if needle in vendor:
            return name
    if Path("/sys/hypervisor/type").exists():
        return _text("/sys/hypervisor/type")
    return ""


def uptime_seconds(proc_root: str = "/proc") -> int:
    first = (_lines(os.path.join(proc_root, "uptime")) or [""])[0]
    try:
        return int(float(first.split()[0]))
    except (ValueError, IndexError):
        return 0


def boot_mode() -> str:
    """"UEFI" or "BIOS" — the presence of efivars is the kernel's own answer."""
    return "UEFI" if Path("/sys/firmware/efi").exists() else "BIOS"


def secure_boot() -> bool | None:
    """None when it cannot be read; a bool is only returned when the efivar is really there."""
    try:
        matches = sorted(Path("/sys/firmware/efi/efivars").glob("SecureBoot-*"))
    except OSError:
        return None
    for path in matches:
        try:
            data = path.read_bytes()
        except OSError:
            continue
        if len(data) >= 5:
            return data[4] == 1
    return None


def disk_usage(path: str = "/") -> tuple[int, int]:
    """(used, total) bytes, or (0, 0) when the filesystem reports a size no real disk has."""
    try:
        stats = os.statvfs(path)
    except OSError:
        return (0, 0)
    total = stats.f_blocks * stats.f_frsize
    if total <= 0 or total >= IMPLAUSIBLE_BYTES:
        return (0, 0)
    free = stats.f_bavail * stats.f_frsize
    return (total - free, total)


def inventory() -> dict[str, Any]:
    """Everything the Settings «О системе» page shows, measured in one pass."""
    memory = meminfo_bytes()
    used, total = disk_usage()
    return {
        "hostname": socket.gethostname(),
        "os": os_name(),
        "kernel": f"{platform.system()} {platform.release()}",
        "architecture": platform.machine(),
        "cpu": cpu_model(),
        "cores": cpu_cores(),
        "memory_total": memory.get("MemTotal", 0),
        "memory_used": memory.get("MemTotal", 0) - memory.get("MemAvailable", 0)
        if "MemAvailable" in memory else 0,
        "swap_total": memory.get("SwapTotal", 0),
        "disk_used": used,
        "disk_total": total,
        "uptime": uptime_seconds(),
        "graphics": graphics(),
        "firmware": firmware(),
        "boot_mode": boot_mode(),
        "secure_boot": secure_boot(),
        "virtualization": virtualization(),
        "session_type": os.environ.get("XDG_SESSION_TYPE", ""),
        "local_time": time.strftime("%d.%m.%Y %H:%M"),
        "timezone": time.tzname[0] if time.tzname else "",
    }
