"""Collect performance metrics from a running system.

Spec PART 5 §1/§4: boot time (firmware → bootloader → kernel → userspace), idle RAM, idle CPU,
process and service counts, disk usage, application startup. Everything here reads real system
sources; when a source is unavailable the metric is reported as ``None`` and the reason is recorded.
Never substitute an estimate for a measurement (PART 1 §15, PART 5 §22).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass, field

BOOT_FIELDS = ("firmware", "loader", "kernel", "initrd", "userspace", "total")
_TIME_RE = re.compile(r"([\d.]+)\s*(min|ms|s)\b")


def parse_duration(text: str) -> float | None:
    """Parse a systemd-analyze duration such as '1min 4.231s' or '812ms' into seconds."""
    matches = _TIME_RE.findall(text)
    if not matches:
        return None
    seconds = 0.0
    for value, unit in matches:
        value = float(value)
        seconds += value * 60 if unit == "min" else value / 1000 if unit == "ms" else value
    return round(seconds, 3)


def parse_systemd_analyze(output: str) -> dict[str, float | None]:
    """Parse `systemd-analyze time` output into per-stage seconds."""
    result: dict[str, float | None] = {field: None for field in BOOT_FIELDS}
    for part in output.replace("\n", " ").split("+"):
        part = part.strip()
        for key in ("firmware", "loader", "kernel", "initrd", "userspace"):
            if f"({key})" in part:
                result[key] = parse_duration(part)
        if "=" in part:
            head, _, tail = part.partition("=")
            for key in ("firmware", "loader", "kernel", "initrd", "userspace"):
                if f"({key})" in head:
                    result[key] = parse_duration(head)
            if "graphical.target" in tail or "reached after" in tail:
                result["total"] = parse_duration(tail)
    if result["total"] is None:
        tail = output.split("=")[-1]
        result["total"] = parse_duration(tail)
    return result


def parse_meminfo(text: str) -> dict[str, int]:
    """Return kB values from /proc/meminfo content."""
    values: dict[str, int] = {}
    for line in text.splitlines():
        key, _, rest = line.partition(":")
        rest = rest.strip().split()
        if rest and rest[0].isdigit():
            values[key.strip()] = int(rest[0])
    return values


def used_ram_mib(meminfo: dict[str, int]) -> float | None:
    """Used RAM = MemTotal - MemAvailable, the only honest 'idle RAM' figure."""
    if "MemTotal" not in meminfo or "MemAvailable" not in meminfo:
        return None
    return round((meminfo["MemTotal"] - meminfo["MemAvailable"]) / 1024, 1)


def read_loadavg(text: str) -> float | None:
    parts = text.split()
    try:
        return float(parts[0])
    except (IndexError, ValueError):
        return None


def count_processes(proc_root: str = "/proc") -> int | None:
    try:
        return sum(1 for name in os.listdir(proc_root) if name.isdigit())
    except OSError:
        return None


def _run(command: list[str], timeout: int = 30) -> str | None:
    if not shutil.which(command[0]):
        return None
    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return completed.stdout if completed.returncode == 0 else None


def measure_app_startup(command: list[str], ready_marker: str | None = None,
                        timeout: int = 60) -> float | None:
    """Wall-clock seconds until `command` exits (or prints `ready_marker`). None if unavailable."""
    if not shutil.which(command[0]):
        return None
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if ready_marker and ready_marker not in (completed.stdout + completed.stderr):
        return None
    return round(time.monotonic() - started, 3)


@dataclass
class Sample:
    """One measurement run. `unavailable` names every metric that could not be measured here."""

    label: str
    timestamp: str
    build: str = "unknown"
    commit: str = "unknown"
    profile: str = "desktop"
    metrics: dict[str, float | int | None] = field(default_factory=dict)
    unavailable: list[str] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True)


def collect(label: str, proc_root: str = "/proc", build: str = "unknown",
            commit: str = "unknown", profile: str = "desktop") -> Sample:
    sample = Sample(
        label=label,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
        build=build,
        commit=commit,
        profile=profile,
    )

    def record(name: str, value, reason: str) -> None:
        sample.metrics[name] = value
        if value is None:
            sample.unavailable.append(f"{name}: {reason}")

    try:
        with open(os.path.join(proc_root, "meminfo"), encoding="utf-8") as handle:
            meminfo = parse_meminfo(handle.read())
    except OSError:
        meminfo = {}
    record("used_ram_mib", used_ram_mib(meminfo), "/proc/meminfo unreadable")

    try:
        with open(os.path.join(proc_root, "loadavg"), encoding="utf-8") as handle:
            load = read_loadavg(handle.read())
    except OSError:
        load = None
    record("loadavg_1m", load, "/proc/loadavg unreadable")
    record("process_count", count_processes(proc_root), "/proc unreadable")

    boot_output = _run(["systemd-analyze", "time"])
    if boot_output is None:
        for name in BOOT_FIELDS:
            record(f"boot_{name}_s", None, "systemd-analyze unavailable (no systemd in this environment)")
    else:
        for name, value in parse_systemd_analyze(boot_output).items():
            record(f"boot_{name}_s", value, "not reported by systemd-analyze")

    units = _run(["systemctl", "list-units", "--type=service", "--state=running", "--no-legend",
                  "--no-pager"])
    if units is None:
        record("running_services", None, "systemctl unavailable")
    else:
        record("running_services", len([l for l in units.splitlines() if l.strip()]), "")

    return sample
