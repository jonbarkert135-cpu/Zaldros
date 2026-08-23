"""Collect a service / dependency / resource map of a running system.

Implements spec PART 1 §7: for every background service answer what it does, whether it is
required, what depends on it, its RAM and CPU cost, its boot-time impact and whether it can be
disabled. Output feeds the performance profiles (§8) and the removal rule in §6.

Pure standard library so it can run inside a minimal VM image with no extra packages.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from typing import Iterable

CLOCK_TICKS = 100  # kernel USER_HZ on all supported architectures


@dataclass
class ServiceInfo:
    unit: str
    description: str = ""
    active_state: str = ""
    sub_state: str = ""
    unit_file_state: str = ""  # enabled / disabled / static / masked
    main_pid: int = 0
    ram_kb: int = 0  # PSS of the whole control group
    cpu_seconds: float = 0.0
    boot_activation_ms: float = 0.0
    required_by: list[str] = field(default_factory=list)
    wanted_by: list[str] = field(default_factory=list)
    part_of: list[str] = field(default_factory=list)

    @property
    def dependants(self) -> list[str]:
        return sorted(set(self.required_by) | set(self.wanted_by) | set(self.part_of))

    @property
    def can_disable(self) -> bool:
        """A unit is safely disable-able only if nothing requires it and it is not static."""
        return self.unit_file_state in {"enabled", "enabled-runtime", "disabled"} and not self.required_by


def _run(cmd: list[str]) -> str:
    """Run a command, returning stdout ('' when the binary or the data is unavailable)."""
    if shutil.which(cmd[0]) is None:
        return ""
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return ""
    return out.stdout if out.returncode == 0 else out.stdout or ""


def parse_show(text: str) -> dict[str, str]:
    """Parse `systemctl show` key=value output."""
    props: dict[str, str] = {}
    for line in text.splitlines():
        if "=" in line:
            key, _, value = line.partition("=")
            props[key.strip()] = value.strip()
    return props


def parse_blame(text: str) -> dict[str, float]:
    """Parse `systemd-analyze blame` into {unit: activation milliseconds}."""
    result: dict[str, float] = {}
    pattern = re.compile(r"^\s*(?:(\d+)min\s*)?(?:([\d.]+)s\s*)?(?:([\d.]+)ms\s*)?(\S+)\s*$")
    for line in text.splitlines():
        match = pattern.match(line)
        if not match:
            continue
        minutes, seconds, millis, unit = match.groups()
        total = 0.0
        if minutes:
            total += float(minutes) * 60_000
        if seconds:
            total += float(seconds) * 1000
        if millis:
            total += float(millis)
        if total:
            result[unit] = round(total, 1)
    return result


def parse_dep_list(value: str) -> list[str]:
    return [item for item in value.split() if item]


def read_pss_kb(pids: Iterable[int], proc_root: str = "/proc") -> int:
    """Sum proportional set size over a set of pids (kB)."""
    total = 0
    for pid in pids:
        try:
            with open(f"{proc_root}/{pid}/smaps_rollup", encoding="utf-8") as handle:
                for line in handle:
                    if line.startswith("Pss:"):
                        total += int(line.split()[1])
                        break
        except (OSError, ValueError):
            continue
    return total


def read_cpu_seconds(props: dict[str, str]) -> float:
    raw = props.get("CPUUsageNSec", "")
    if raw.isdigit():
        return round(int(raw) / 1e9, 2)
    return 0.0


def list_service_units() -> list[str]:
    text = _run(["systemctl", "list-units", "--type=service", "--all", "--no-legend", "--plain"])
    units = []
    for line in text.splitlines():
        parts = line.split()
        if parts and parts[0].endswith(".service"):
            units.append(parts[0])
    return units


def collect(units: list[str] | None = None) -> list[ServiceInfo]:
    blame = parse_blame(_run(["systemd-analyze", "blame", "--no-pager"]))
    services: list[ServiceInfo] = []
    for unit in units if units is not None else list_service_units():
        props = parse_show(_run(["systemctl", "show", unit, "--no-pager"]))
        if not props:
            continue
        info = ServiceInfo(
            unit=unit,
            description=props.get("Description", ""),
            active_state=props.get("ActiveState", ""),
            sub_state=props.get("SubState", ""),
            unit_file_state=props.get("UnitFileState", ""),
            main_pid=int(props.get("MainPID", "0") or 0),
            cpu_seconds=read_cpu_seconds(props),
            boot_activation_ms=blame.get(unit, 0.0),
            required_by=parse_dep_list(props.get("RequiredBy", "")),
            wanted_by=parse_dep_list(props.get("WantedBy", "")),
            part_of=parse_dep_list(props.get("PartOf", "")),
        )
        if info.main_pid:
            info.ram_kb = read_pss_kb([info.main_pid])
        services.append(info)
    return services


def to_dicts(services: list[ServiceInfo]) -> list[dict]:
    rows = []
    for service in services:
        row = asdict(service)
        row["dependants"] = service.dependants
        row["can_disable"] = service.can_disable
        rows.append(row)
    return rows


def to_json(services: list[ServiceInfo]) -> str:
    return json.dumps({"services": to_dicts(services)}, indent=2, sort_keys=True)


def to_markdown(services: list[ServiceInfo]) -> str:
    running = [s for s in services if s.active_state == "active"]
    total_ram = sum(s.ram_kb for s in services)
    lines = [
        "# Bedrock Linux — service / dependency map",
        "",
        f"Services inspected: **{len(services)}** — active: **{len(running)}** — "
        f"resident (PSS of main processes): **{total_ram / 1024:.1f} MB**",
        "",
        "| Unit | Purpose | State | Enabled | RAM (MB) | CPU (s) | Boot (ms) | Depended on by | Disable? |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | --- | --- |",
    ]
    for service in sorted(services, key=lambda s: (-s.ram_kb, s.unit)):
        dependants = ", ".join(service.dependants) or "—"
        lines.append(
            f"| `{service.unit}` | {service.description or '—'} | {service.active_state}"
            f"/{service.sub_state} | {service.unit_file_state or '—'} | {service.ram_kb / 1024:.1f} | "
            f"{service.cpu_seconds:.2f} | {service.boot_activation_ms:.0f} | {dependants} | "
            f"{'yes' if service.can_disable else 'no'} |"
        )
    lines += [
        "",
        "> A service may only be disabled in a performance profile after its purpose, dependants and "
        "consequences are understood (spec PART 1 §6, §7). `Disable? = yes` means *no unit requires it*, "
        "not that disabling it is safe for security or hardware support.",
    ]
    return "\n".join(lines) + "\n"
