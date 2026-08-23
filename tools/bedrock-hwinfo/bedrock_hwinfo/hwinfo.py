"""Hardware and system inventory collected from real kernel interfaces.

Backend for Bedrock Device Manager (spec PART 3 §8) and Bedrock System Information (§13).
Hard rule from §21: every value must come from a real kernel source. Nothing is invented; a field
that cannot be read is reported as ``None`` and rendered as "unknown", never guessed.

Sources: /proc/cpuinfo, /proc/meminfo, /sys/class/dmi/id, /sys/block, /sys/class/net,
/sys/class/drm, /sys/class/power_supply, /proc/uptime, /etc/os-release, uname.
"""

from __future__ import annotations

import json
import os
import platform
from dataclasses import asdict, dataclass, field

SYS = "/sys"
PROC = "/proc"


def read_text(path: str) -> str | None:
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read().strip()
    except OSError:
        return None


def read_int(path: str) -> int | None:
    value = read_text(path)
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _listdir(path: str) -> list[str]:
    try:
        return sorted(os.listdir(path))
    except OSError:
        return []


@dataclass
class Cpu:
    model: str | None = None
    vendor: str | None = None
    logical_cores: int = 0
    architecture: str | None = None
    max_mhz: float | None = None
    flags_of_interest: list[str] = field(default_factory=list)


@dataclass
class Memory:
    total_kb: int | None = None
    available_kb: int | None = None
    swap_total_kb: int | None = None


@dataclass
class Disk:
    name: str
    size_bytes: int | None = None
    model: str | None = None
    rotational: bool | None = None
    removable: bool | None = None


@dataclass
class NetworkInterface:
    name: str
    mac: str | None = None
    state: str | None = None
    speed_mbps: int | None = None
    wireless: bool = False


@dataclass
class Display:
    connector: str
    status: str | None = None
    modes: int = 0


@dataclass
class Battery:
    name: str
    technology: str | None = None
    capacity_percent: int | None = None
    status: str | None = None


@dataclass
class SystemInfo:
    os_name: str | None = None
    os_version: str | None = None
    kernel: str | None = None
    hostname: str | None = None
    uptime_seconds: float | None = None
    board_vendor: str | None = None
    board_name: str | None = None
    product_name: str | None = None
    firmware_vendor: str | None = None
    firmware_version: str | None = None


@dataclass
class Inventory:
    system: SystemInfo
    cpu: Cpu
    memory: Memory
    disks: list[Disk]
    network: list[NetworkInterface]
    displays: list[Display]
    batteries: list[Battery]


INTERESTING_FLAGS = ("vmx", "svm", "aes", "avx2", "avx512f", "sha_ni")


def parse_cpuinfo(text: str) -> Cpu:
    cpu = Cpu(architecture=platform.machine())
    cores = 0
    for line in text.splitlines():
        key, _, value = line.partition(":")
        key, value = key.strip(), value.strip()
        if key == "processor":
            cores += 1
        elif key == "model name" and not cpu.model:
            cpu.model = value
        elif key == "vendor_id" and not cpu.vendor:
            cpu.vendor = value
        elif key == "flags" and not cpu.flags_of_interest:
            present = set(value.split())
            cpu.flags_of_interest = [f for f in INTERESTING_FLAGS if f in present]
    cpu.logical_cores = cores
    return cpu


def parse_meminfo(text: str) -> Memory:
    values: dict[str, int] = {}
    for line in text.splitlines():
        key, _, rest = line.partition(":")
        parts = rest.split()
        if parts and parts[0].isdigit():
            values[key.strip()] = int(parts[0])
    return Memory(
        total_kb=values.get("MemTotal"),
        available_kb=values.get("MemAvailable"),
        swap_total_kb=values.get("SwapTotal"),
    )


def parse_os_release(text: str) -> tuple[str | None, str | None]:
    data: dict[str, str] = {}
    for line in text.splitlines():
        key, _, value = line.partition("=")
        data[key.strip()] = value.strip().strip('"')
    return data.get("NAME"), data.get("VERSION") or data.get("VERSION_ID")


def collect_cpu(proc: str = PROC) -> Cpu:
    text = read_text(f"{proc}/cpuinfo")
    return parse_cpuinfo(text) if text else Cpu(architecture=platform.machine())


def collect_memory(proc: str = PROC) -> Memory:
    text = read_text(f"{proc}/meminfo")
    return parse_meminfo(text) if text else Memory()


def collect_disks(sysfs: str = SYS) -> list[Disk]:
    disks: list[Disk] = []
    for name in _listdir(f"{sysfs}/block"):
        if name.startswith(("loop", "ram", "zram", "dm-")):
            continue
        base = f"{sysfs}/block/{name}"
        sectors = read_int(f"{base}/size")
        rotational = read_int(f"{base}/queue/rotational")
        removable = read_int(f"{base}/removable")
        disks.append(
            Disk(
                name=name,
                size_bytes=sectors * 512 if sectors is not None else None,
                model=read_text(f"{base}/device/model"),
                rotational=None if rotational is None else bool(rotational),
                removable=None if removable is None else bool(removable),
            )
        )
    return disks


def collect_network(sysfs: str = SYS) -> list[NetworkInterface]:
    interfaces: list[NetworkInterface] = []
    for name in _listdir(f"{sysfs}/class/net"):
        if name == "lo":
            continue
        base = f"{sysfs}/class/net/{name}"
        interfaces.append(
            NetworkInterface(
                name=name,
                mac=read_text(f"{base}/address"),
                state=read_text(f"{base}/operstate"),
                speed_mbps=read_int(f"{base}/speed"),
                wireless=os.path.isdir(f"{base}/wireless") or os.path.exists(f"{base}/phy80211"),
            )
        )
    return interfaces


def collect_displays(sysfs: str = SYS) -> list[Display]:
    displays: list[Display] = []
    for name in _listdir(f"{sysfs}/class/drm"):
        if "-" not in name:  # skip card0, renderD128
            continue
        base = f"{sysfs}/class/drm/{name}"
        modes = read_text(f"{base}/modes") or ""
        displays.append(
            Display(
                connector=name.split("-", 1)[1],
                status=read_text(f"{base}/status"),
                modes=len([m for m in modes.splitlines() if m.strip()]),
            )
        )
    return displays


def collect_batteries(sysfs: str = SYS) -> list[Battery]:
    batteries: list[Battery] = []
    for name in _listdir(f"{sysfs}/class/power_supply"):
        base = f"{sysfs}/class/power_supply/{name}"
        if (read_text(f"{base}/type") or "").lower() != "battery":
            continue
        batteries.append(
            Battery(
                name=name,
                technology=read_text(f"{base}/technology"),
                capacity_percent=read_int(f"{base}/capacity"),
                status=read_text(f"{base}/status"),
            )
        )
    return batteries


def collect_system(sysfs: str = SYS, proc: str = PROC) -> SystemInfo:
    os_release = read_text("/etc/os-release")
    os_name, os_version = parse_os_release(os_release) if os_release else (None, None)
    uptime_raw = read_text(f"{proc}/uptime")
    uptime = None
    if uptime_raw:
        try:
            uptime = float(uptime_raw.split()[0])
        except (ValueError, IndexError):
            uptime = None
    dmi = f"{sysfs}/class/dmi/id"
    return SystemInfo(
        os_name=os_name,
        os_version=os_version,
        kernel=platform.release(),
        hostname=platform.node() or None,
        uptime_seconds=uptime,
        board_vendor=read_text(f"{dmi}/board_vendor"),
        board_name=read_text(f"{dmi}/board_name"),
        product_name=read_text(f"{dmi}/product_name"),
        firmware_vendor=read_text(f"{dmi}/bios_vendor"),
        firmware_version=read_text(f"{dmi}/bios_version"),
    )


def collect(sysfs: str = SYS, proc: str = PROC) -> Inventory:
    return Inventory(
        system=collect_system(sysfs, proc),
        cpu=collect_cpu(proc),
        memory=collect_memory(proc),
        disks=collect_disks(sysfs),
        network=collect_network(sysfs),
        displays=collect_displays(sysfs),
        batteries=collect_batteries(sysfs),
    )


def _fmt(value, suffix: str = "") -> str:
    return "unknown" if value is None else f"{value}{suffix}"


def _gib(value_bytes: int | None) -> str:
    return "unknown" if value_bytes is None else f"{value_bytes / 1024**3:.1f} GiB"


def to_json(inventory: Inventory) -> str:
    return json.dumps(asdict(inventory), indent=2, sort_keys=True)


def to_markdown(inventory: Inventory) -> str:
    system, cpu, memory = inventory.system, inventory.cpu, inventory.memory
    lines = [
        "# Bedrock Linux — system & device inventory",
        "",
        "## System",
        f"- OS: {_fmt(system.os_name)} {_fmt(system.os_version)}",
        f"- Kernel: {_fmt(system.kernel)}",
        f"- Host: {_fmt(system.hostname)}",
        f"- Machine: {_fmt(system.product_name)} ({_fmt(system.board_vendor)} {_fmt(system.board_name)})",
        f"- Firmware: {_fmt(system.firmware_vendor)} {_fmt(system.firmware_version)}",
        f"- Uptime: {'unknown' if system.uptime_seconds is None else f'{system.uptime_seconds / 3600:.1f} h'}",
        "",
        "## CPU",
        f"- Model: {_fmt(cpu.model)}",
        f"- Vendor: {_fmt(cpu.vendor)} — architecture {_fmt(cpu.architecture)}",
        f"- Logical cores: {cpu.logical_cores}",
        f"- Notable features: {', '.join(cpu.flags_of_interest) or 'unknown'}",
        "",
        "## Memory",
        f"- Total: {'unknown' if memory.total_kb is None else f'{memory.total_kb / 1024**2:.1f} GiB'}",
        f"- Available: {'unknown' if memory.available_kb is None else f'{memory.available_kb / 1024**2:.1f} GiB'}",
        f"- Swap: {'unknown' if memory.swap_total_kb is None else f'{memory.swap_total_kb / 1024**2:.1f} GiB'}",
        "",
        "## Storage",
        "| Device | Size | Model | Type | Removable |",
        "| --- | --- | --- | --- | --- |",
    ]
    for disk in inventory.disks:
        kind = "unknown" if disk.rotational is None else ("HDD" if disk.rotational else "SSD/NVMe")
        lines.append(
            f"| `{disk.name}` | {_gib(disk.size_bytes)} | {_fmt(disk.model)} | {kind} | "
            f"{_fmt(disk.removable)} |"
        )
    lines += ["", "## Network", "| Interface | MAC | State | Speed | Wireless |", "| --- | --- | --- | --- | --- |"]
    for nic in inventory.network:
        speed = "unknown" if nic.speed_mbps is None or nic.speed_mbps < 0 else f"{nic.speed_mbps} Mb/s"
        lines.append(f"| `{nic.name}` | {_fmt(nic.mac)} | {_fmt(nic.state)} | {speed} | {nic.wireless} |")
    lines += ["", "## Displays"]
    lines += [
        f"- {display.connector}: {_fmt(display.status)}, {display.modes} modes"
        for display in inventory.displays
    ] or ["- none detected"]
    lines += ["", "## Batteries"]
    lines += [
        f"- {battery.name}: {_fmt(battery.capacity_percent, '%')} ({_fmt(battery.status)}, "
        f"{_fmt(battery.technology)})"
        for battery in inventory.batteries
    ] or ["- none detected"]
    lines += [
        "",
        "> Every value above is read from the kernel (`/proc`, `/sys`). Fields that cannot be read are "
        "reported as `unknown` — Bedrock never fabricates hardware information (spec PART 3 §21).",
    ]
    return "\n".join(lines) + "\n"
