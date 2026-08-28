# SPDX-License-Identifier: GPL-3.0-or-later
"""Processes and system counters — the data behind Zaldros «Диспетчер задач».

Everything here is read from the kernel's own files: `/proc/<pid>/{stat,status,cmdline,io,fd}`,
`/proc/stat`, `/proc/meminfo`, `/proc/diskstats`, `/proc/net/dev`, `/sys/class/drm`. No `ps`, no
`top`, no psutil: those are three ways of reading the same files, and two of them would be a new
runtime dependency on the ISO.

Two rules the Windows Task Manager also follows, and which the honesty contract makes explicit:

* **CPU load is a difference of two samples.** One reading of `/proc/<pid>/stat` says how much CPU
  a process has used since boot, which is not what a user means by «нагрузка». `Sampler` keeps the
  previous sample; the very first `sample()` returns processes with `cpu=None` — an unknown, not a
  zero. Nothing here invents a number to fill a column.
* **Nothing samples in the background.** `Sampler` only reads when someone calls it, which happens
  while the Task Manager window is open. Closing the window stops all of it (ADR-0014).

Grouping into «Приложения» / «Фоновые процессы» is deliberately not a guess about window
ownership: a process is an application when the caller passes a set of pids that own windows, and
the compositor is the only thing that knows that. Without such a set every process is listed as a
background process, which is what a machine without a compositor really has.
"""

from __future__ import annotations

import errno
import dataclasses
import os
import pwd
import signal
import time
from dataclasses import dataclass, field
from pathlib import Path

from .reading import NO_DATA, Reading

CLOCK_TICKS = os.sysconf("SC_CLK_TCK") if hasattr(os, "sysconf") else 100
PAGE_SIZE = os.sysconf("SC_PAGE_SIZE") if hasattr(os, "sysconf") else 4096

# /proc/<pid>/stat state letters, in the words the shell shows.
STATE_TEXT = {"R": "выполняется", "S": "ожидание", "D": "непрерываемый ввод-вывод",
              "Z": "зомби", "T": "остановлен", "t": "трассировка", "I": "простой",
              "X": "завершён"}

# Kernel threads have no command line at all; Windows hides them under «Процессы Windows», we
# label them honestly instead of pretending they are applications.
KERNEL_THREAD = "процесс ядра"

# Enough to name a card without shipping a 2 MB pci.ids (same table as hardware.py uses).
_GPU_VENDORS = {"0x8086": "Intel", "0x10de": "NVIDIA", "0x1002": "AMD", "0x1af4": "Red Hat",
                "0x1234": "QEMU", "0x15ad": "VMware", "0x1414": "Microsoft", "0x1b36": "QEMU"}


def _text(path: str | Path) -> str:
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _int(value: str, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class Process:
    """One process, as the kernel describes it right now.

    `cpu` is None until two samples exist. `rss` is resident memory in bytes — the column Windows
    calls «Память», and the only memory number that is not double counted across a process tree.
    """

    pid: int
    ppid: int
    name: str
    cmdline: str
    user: str
    state: str
    threads: int
    rss: int
    cpu_seconds: float
    started: float                     # seconds since boot
    cpu: float | None = None
    read_bytes: int | None = None
    write_bytes: int | None = None
    open_files: int | None = None
    is_kernel: bool = False

    @property
    def state_text(self) -> str:
        return STATE_TEXT.get(self.state, self.state)

    def as_row(self) -> dict:
        """The shape QML consumes. `cpu` stays None so the view can show a dash."""
        return {"pid": self.pid, "ppid": self.ppid, "name": self.name, "cmdline": self.cmdline,
                "user": self.user, "state": self.state, "stateText": self.state_text,
                "threads": self.threads, "rss": self.rss, "cpu": self.cpu,
                "readBytes": self.read_bytes, "writeBytes": self.write_bytes,
                "openFiles": self.open_files, "isKernel": self.is_kernel,
                "cpuSeconds": self.cpu_seconds, "started": self.started}


def _user_name(uid: int) -> str:
    try:
        return pwd.getpwuid(uid).pw_name
    except KeyError:
        return str(uid)


def read_process(pid: int, proc_root: str = "/proc", with_io: bool = False) -> Process | None:
    """Read one process, or None when it disappeared mid-read (a race, not an error)."""
    base = os.path.join(proc_root, str(pid))
    stat = _text(os.path.join(base, "stat"))
    if not stat:
        return None
    # The comm field is parenthesised and may itself contain spaces and brackets: split on the
    # last ')' rather than on whitespace, which is the bug every naive /proc parser has.
    head, _, tail = stat.partition("(")
    comm, _, rest = tail.rpartition(")")
    fields = rest.split()
    if len(fields) < 22:
        return None
    state = fields[0]
    ppid = _int(fields[1])
    utime, stime = _int(fields[11]), _int(fields[12])
    threads = _int(fields[17])
    starttime = _int(fields[19])
    rss = _int(fields[21]) * PAGE_SIZE

    status = _text(os.path.join(base, "status"))
    uid = 0
    for line in status.splitlines():
        if line.startswith("Uid:"):
            parts = line.split()
            if len(parts) > 1:
                uid = _int(parts[1])
            break

    cmdline = _text(os.path.join(base, "cmdline")).replace("\0", " ").strip()
    is_kernel = not cmdline
    read_bytes = write_bytes = open_files = None
    if with_io:
        for line in _text(os.path.join(base, "io")).splitlines():
            key, _, value = line.partition(":")
            if key == "read_bytes":
                read_bytes = _int(value.strip())
            elif key == "write_bytes":
                write_bytes = _int(value.strip())
        try:
            open_files = len(os.listdir(os.path.join(base, "fd")))
        except OSError:
            open_files = None            # not ours to read: unknown, not zero

    return Process(pid=pid, ppid=ppid, name=comm or head.strip(),
                   cmdline=cmdline or KERNEL_THREAD, user=_user_name(uid), state=state,
                   threads=threads, rss=rss, cpu_seconds=(utime + stime) / CLOCK_TICKS,
                   started=starttime / CLOCK_TICKS, read_bytes=read_bytes,
                   write_bytes=write_bytes, open_files=open_files, is_kernel=is_kernel)


def pids(proc_root: str = "/proc") -> list[int]:
    try:
        return sorted(int(name) for name in os.listdir(proc_root) if name.isdigit())
    except OSError:
        return []


def total_cpu_times(proc_root: str = "/proc") -> tuple[float, float] | None:
    """(busy, total) seconds from the aggregate line of /proc/stat."""
    line = (_text(os.path.join(proc_root, "stat")).splitlines() or [""])[0]
    parts = line.split()
    if not parts or parts[0] != "cpu":
        return None
    values = [_int(value) for value in parts[1:]]
    if len(values) < 4:
        return None
    total = sum(values) / CLOCK_TICKS
    idle = (values[3] + (values[4] if len(values) > 4 else 0)) / CLOCK_TICKS
    return (total - idle, total)


def per_core_times(proc_root: str = "/proc") -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    for line in _text(os.path.join(proc_root, "stat")).splitlines():
        parts = line.split()
        if not parts or not parts[0].startswith("cpu") or parts[0] == "cpu":
            continue
        values = [_int(value) for value in parts[1:]]
        if len(values) < 4:
            continue
        total = sum(values) / CLOCK_TICKS
        idle = (values[3] + (values[4] if len(values) > 4 else 0)) / CLOCK_TICKS
        out.append((total - idle, total))
    return out


def disk_counters(proc_root: str = "/proc") -> tuple[int, int]:
    """(bytes read, bytes written) across whole disks. Partitions are skipped so the same write
    is not counted twice — /proc/diskstats lists sda and sda1 side by side."""
    read = written = 0
    for line in _text(os.path.join(proc_root, "diskstats")).splitlines():
        parts = line.split()
        if len(parts) < 10:
            continue
        name = parts[2]
        if name[-1].isdigit() and not name.startswith(("nvme", "mmcblk")):
            continue                      # sda1 is inside sda
        if name.startswith(("loop", "ram", "zram")):
            continue
        if name.startswith(("nvme", "mmcblk")) and "p" in name.split("n")[-1]:
            continue                      # nvme0n1p1 is inside nvme0n1
        read += _int(parts[5]) * 512      # sectors are 512 bytes in /proc/diskstats, always
        written += _int(parts[9]) * 512
    return (read, written)


def net_counters(proc_root: str = "/proc") -> tuple[int, int]:
    """(bytes received, bytes sent), loopback excluded — traffic with yourself is not network."""
    received = sent = 0
    for line in _text(os.path.join(proc_root, "net/dev")).splitlines()[2:]:
        name, _, rest = line.partition(":")
        parts = rest.split()
        if name.strip() == "lo" or len(parts) < 9:
            continue
        received += _int(parts[0])
        sent += _int(parts[8])
    return (received, sent)


def gpus(drm_root: str = "/sys/class/drm") -> list[Reading]:
    """Every render node the kernel knows, with its driver and — when the driver exports it —
    its real load. amdgpu publishes `gpu_busy_percent`; i915 and nouveau do not, and no number is
    invented for them: the card is listed with a reason instead of a plausible percentage."""
    out: list[Reading] = []
    try:
        cards = sorted(path for path in Path(drm_root).glob("card[0-9]*") if "-" not in path.name)
    except OSError:
        return out
    for card in cards:
        device = card / "device"
        vendor = _text(device / "vendor").strip()
        driver = ""
        try:
            driver = os.path.basename(os.readlink(device / "driver"))
        except OSError:
            pass
        busy_file = device / "gpu_busy_percent"
        busy = _text(busy_file).strip()
        name = f"{_GPU_VENDORS.get(vendor, vendor or 'GPU')} ({driver or 'драйвер неизвестен'})"
        if busy.isdigit():
            out.append(Reading.measured(int(busy), name, str(busy_file), card=card.name,
                                        driver=driver))
        else:
            out.append(Reading(False, None, name, str(card),
                               {"card": card.name, "driver": driver,
                                "reason": "драйвер не сообщает загрузку"}))
    return out


@dataclass
class Snapshot:
    """Everything one refresh of the Task Manager needs, measured in a single pass."""

    processes: list[Process] = field(default_factory=list)
    cpu: float | None = None
    cores: list[float] = field(default_factory=list)
    memory_used: int = 0
    memory_total: int = 0
    swap_used: int = 0
    swap_total: int = 0
    disk_read_rate: float | None = None
    disk_write_rate: float | None = None
    net_recv_rate: float | None = None
    net_sent_rate: float | None = None
    uptime: int = 0
    elapsed: float = 0.0

    @property
    def memory_percent(self) -> int | None:
        if not self.memory_total:
            return None
        return round(self.memory_used / self.memory_total * 100)


class Sampler:
    """Two samples make a rate. Holds the previous one and nothing else.

    Deliberately not a thread and not a timer: the caller decides when to sample, and when the
    window closes the caller simply stops calling. That is how «no background polling» is enforced
    structurally rather than by discipline.
    """

    def __init__(self, proc_root: str = "/proc", clock=time.monotonic) -> None:
        self.proc_root = proc_root
        self._clock = clock
        self._previous_cpu: dict[int, float] = {}
        self._previous_total: tuple[float, float] | None = None
        self._previous_cores: list[tuple[float, float]] = []
        self._previous_disk: tuple[int, int] | None = None
        self._previous_net: tuple[int, int] | None = None
        self._previous_at: float | None = None

    def sample(self, with_io: bool = False) -> Snapshot:
        now = self._clock()
        elapsed = 0.0 if self._previous_at is None else max(now - self._previous_at, 0.0)

        processes: list[Process] = []
        cpu_now: dict[int, float] = {}
        for pid in pids(self.proc_root):
            process = read_process(pid, self.proc_root, with_io=with_io)
            if process is None:
                continue
            cpu_now[pid] = process.cpu_seconds
            share: float | None = None
            previous = self._previous_cpu.get(pid)
            if previous is not None and elapsed > 0:
                delta = max(process.cpu_seconds - previous, 0.0)
                share = round(delta / elapsed * 100, 1)
            processes.append(dataclasses.replace(process, cpu=share))
        self._previous_cpu = cpu_now

        total = total_cpu_times(self.proc_root)
        cpu_percent = None
        if total and self._previous_total:
            busy = total[0] - self._previous_total[0]
            span = total[1] - self._previous_total[1]
            cpu_percent = round(busy / span * 100, 1) if span > 0 else None
        self._previous_total = total

        cores_now = per_core_times(self.proc_root)
        cores: list[float] = []
        if self._previous_cores and len(self._previous_cores) == len(cores_now):
            for (busy, span), (was_busy, was_span) in zip(cores_now, self._previous_cores):
                delta = span - was_span
                cores.append(round((busy - was_busy) / delta * 100, 1) if delta > 0 else 0.0)
        self._previous_cores = cores_now

        from . import hardware
        memory = hardware.meminfo_bytes(self.proc_root)
        memory_total = memory.get("MemTotal", 0)
        memory_used = memory_total - memory.get("MemAvailable", memory_total)
        swap_total = memory.get("SwapTotal", 0)
        swap_used = swap_total - memory.get("SwapFree", swap_total)

        disk = disk_counters(self.proc_root)
        net = net_counters(self.proc_root)
        rates: dict[str, float | None] = {"dr": None, "dw": None, "nr": None, "ns": None}
        if elapsed > 0 and self._previous_disk and self._previous_net:
            rates["dr"] = max(disk[0] - self._previous_disk[0], 0) / elapsed
            rates["dw"] = max(disk[1] - self._previous_disk[1], 0) / elapsed
            rates["nr"] = max(net[0] - self._previous_net[0], 0) / elapsed
            rates["ns"] = max(net[1] - self._previous_net[1], 0) / elapsed
        self._previous_disk, self._previous_net = disk, net
        self._previous_at = now

        return Snapshot(processes=processes, cpu=cpu_percent, cores=cores,
                        memory_used=max(memory_used, 0), memory_total=memory_total,
                        swap_used=max(swap_used, 0), swap_total=swap_total,
                        disk_read_rate=rates["dr"], disk_write_rate=rates["dw"],
                        net_recv_rate=rates["nr"], net_sent_rate=rates["ns"],
                        uptime=hardware.uptime_seconds(self.proc_root), elapsed=elapsed)


class ProcessFacet:
    """The facet the shell talks to: sample, group, end, inspect, autostart.

    Ending a process is the one destructive thing the Task Manager can do, so it is the one place
    with a two-step contract: SIGTERM first, SIGKILL only when the caller explicitly asks, and the
    refusal from the kernel (EPERM) is passed through verbatim instead of being reported as done.
    """

    def __init__(self, proc_root: str = "/proc", sampler: Sampler | None = None) -> None:
        self.proc_root = proc_root
        self.sampler = sampler if sampler is not None else Sampler(proc_root)

    # -- reading ---------------------------------------------------------------------------
    def sample(self, with_io: bool = False) -> Snapshot:
        return self.sampler.sample(with_io=with_io)

    def process(self, pid: int, with_io: bool = True) -> Reading:
        found = read_process(pid, self.proc_root, with_io=with_io)
        if found is None:
            return Reading.missing("процесс завершился", f"{self.proc_root}/{pid}")
        return Reading.measured(found.pid, found.name, f"{self.proc_root}/{pid}",
                                **found.as_row())

    def group(self, snapshot: Snapshot, window_pids: set[int] | None = None) -> dict:
        """Windows's three sections. Without a compositor there is no «Приложения» section, and
        that is stated rather than faked by guessing at process names."""
        windows = window_pids or set()
        apps, background, system = [], [], []
        for process in snapshot.processes:
            if process.pid in windows:
                apps.append(process)
            elif process.is_kernel or process.user == "root":
                system.append(process)
            else:
                background.append(process)
        return {"apps": apps, "background": background, "system": system,
                "apps_available": bool(window_pids),
                "apps_reason": "" if window_pids else "нет списка окон от композитора"}

    # -- acting ----------------------------------------------------------------------------
    def end(self, pid: int, force: bool = False) -> Reading:
        """SIGTERM, or SIGKILL when `force`. Returns what the kernel actually did."""
        if pid <= 1:
            return Reading.missing("нельзя завершить init", str(pid))
        try:
            os.kill(pid, signal.SIGKILL if force else signal.SIGTERM)
        except ProcessLookupError:
            return Reading.missing("процесс уже завершился", str(pid))
        except PermissionError:
            return Reading.missing("недостаточно прав", str(pid))
        except OSError as error:
            return Reading.missing(os.strerror(error.errno or errno.EINVAL), str(pid))
        return Reading.measured(pid, "SIGKILL" if force else "SIGTERM", str(pid), forced=force)

    def alive(self, pid: int) -> bool:
        return os.path.isdir(os.path.join(self.proc_root, str(pid)))

    # -- startup ---------------------------------------------------------------------------
    def startup(self, autostart_dirs: list[str] | None = None) -> list[Reading]:
        """What the session starts at login: freedesktop autostart entries.

        `Hidden=true` is the standard's way of disabling an entry, which is exactly what the
        Windows «Автозагрузка» toggle needs — no invented registry of our own.
        """
        directories = autostart_dirs if autostart_dirs is not None else _autostart_dirs()
        seen: dict[str, Reading] = {}
        for directory in directories:
            try:
                entries = sorted(Path(directory).glob("*.desktop"))
            except OSError:
                continue
            for entry in entries:
                values = _desktop_values(entry)
                if not values.get("Name"):
                    continue
                hidden = values.get("Hidden", "").lower() == "true"
                seen[entry.name] = Reading.measured(
                    None, values["Name"], str(entry), file=str(entry), entry=entry.name,
                    enabled=not hidden, command=values.get("Exec", ""),
                    writable=os.access(entry.parent, os.W_OK),
                    comment=values.get("Comment", ""))
        return sorted(seen.values(), key=lambda item: item.detail.lower())

    def set_startup_enabled(self, entry_path: str, enabled: bool) -> Reading:
        """Toggle an autostart entry by writing `Hidden=` into the user's own copy.

        System entries in /etc/xdg are never edited: the standard says a user copy in
        ~/.config/autostart shadows them, so the toggle creates that copy instead.
        """
        source = Path(entry_path)
        if not source.is_file():
            return Reading.missing(NO_DATA, entry_path)
        target = Path(_user_autostart_dir()) / source.name
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            lines = source.read_text(encoding="utf-8", errors="replace").splitlines()
            out, written = [], False
            for line in lines:
                if line.split("=")[0].strip() == "Hidden":
                    if not written:
                        out.append(f"Hidden={'false' if enabled else 'true'}")
                        written = True
                    continue
                out.append(line)
            if not written:
                out.append(f"Hidden={'false' if enabled else 'true'}")
            temporary = target.with_suffix(".desktop.tmp")
            temporary.write_text("\n".join(out) + "\n", encoding="utf-8")
            os.replace(temporary, target)       # atomic: no half-written autostart entry
        except OSError as error:
            return Reading.missing(os.strerror(error.errno or errno.EIO), str(target))
        return Reading.measured(None, str(target), str(target), enabled=enabled)


def _autostart_dirs() -> list[str]:
    config_home = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    dirs = [os.path.join(path, "autostart")
            for path in (os.environ.get("XDG_CONFIG_DIRS") or "/etc/xdg").split(":") if path]
    return dirs + [os.path.join(config_home, "autostart")]   # user copy last: it wins


def _user_autostart_dir() -> str:
    config_home = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(config_home, "autostart")


def _desktop_values(path: Path) -> dict[str, str]:
    """Only the [Desktop Entry] group, only the keys we use, localised names preferred."""
    values: dict[str, str] = {}
    in_group = False
    language = (os.environ.get("LC_ALL") or os.environ.get("LANG") or "").split(".")[0].split("_")[0]
    for line in _text(path).splitlines():
        line = line.strip()
        if line.startswith("["):
            in_group = line == "[Desktop Entry]"
            continue
        if not in_group or "=" not in line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if key == f"Name[{language}]" and language:
            values["Name"] = value
        elif key in ("Name", "Exec", "Hidden", "Comment") and key not in values:
            values[key] = value
    return values
