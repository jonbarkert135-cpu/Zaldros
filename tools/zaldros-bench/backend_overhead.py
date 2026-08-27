#!/usr/bin/env python3
"""Measure what the shell costs while nothing is happening.

An idle desktop is the case that matters: it is 99 % of a laptop's day and all of its battery.
This runs the real shell — the real QML, the real models, the real event loop — offscreen for a
fixed wall-clock window and reports what the kernel says it spent.

    uv run --python shell/zaldros-shell/.venv/bin/python \\
        tools/zaldros-bench/backend_overhead.py --seconds 60

What is measured, and where the number comes from:

  cpu_seconds     utime + stime from /proc/self/stat, in seconds. The process's own CPU time; the
                  only figure here that is a cost rather than a proxy for one.
  voluntary_ctx   voluntary_ctxt_switches from /proc/self/status — how many times the process went
                  to sleep and was woken. A 1 Hz timer shows up here as ~1 per second.
  proc_reads      how many times /proc/stat and /proc/meminfo were opened, counted by wrapping
                  the reader. This is the cost the old clock tick dragged along with it.
  signals         Qt signal emissions from ShellState, each of which re-evaluates every QML
                  binding that reads it.

`--mode legacy` reproduces the behaviour before the backend (a 1 Hz QTimer driving clock and
meters together, `memoryPercent` re-reading /proc/meminfo on every evaluation) so the two numbers
are produced by the same harness on the same machine in the same run. Comparing against a number
written down on another day is not a measurement.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "shell" / "zaldros-shell"))
sys.path.insert(0, str(REPO / "backend"))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QTimer  # noqa: E402

from zaldros_shell import model                      # noqa: E402
from zaldros_shell.model import ShellState           # noqa: E402


def cpu_seconds() -> float:
    """utime + stime of this process, in seconds."""
    with open("/proc/self/stat", encoding="utf-8") as handle:
        fields = handle.read().rpartition(")")[2].split()
    ticks = os.sysconf("SC_CLK_TCK")
    return (int(fields[11]) + int(fields[12])) / ticks


def context_switches() -> tuple[int, int]:
    voluntary = involuntary = 0
    try:
        with open("/proc/self/status", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("voluntary_ctxt_switches:"):
                    voluntary = int(line.split()[1])
                elif line.startswith("nonvoluntary_ctxt_switches:"):
                    involuntary = int(line.split()[1])
    except OSError:
        pass
    return voluntary, involuntary


class Counters:
    """Counts every /proc read the shell makes, by wrapping the readers it imports."""

    def __init__(self) -> None:
        self.proc_reads = 0
        self.signals = 0
        self._original = (model.cpu_times, model.memory_percent)

    def install(self) -> None:
        cpu_times, memory_percent = self._original

        def counted_cpu(*args, **kwargs):
            self.proc_reads += 1
            return cpu_times(*args, **kwargs)

        def counted_memory(*args, **kwargs):
            self.proc_reads += 1
            return memory_percent(*args, **kwargs)

        model.cpu_times = counted_cpu
        model.memory_percent = counted_memory

    def restore(self) -> None:
        model.cpu_times, model.memory_percent = self._original


class LegacyState(ShellState):
    """The shell as it behaved before the backend: one 1 Hz timer for everything.

    Deliberately a subclass rather than a copy of the old file, so the comparison is between two
    behaviours of the same code and not between two different programs.
    """

    def __init__(self, locale: str = "ru") -> None:
        super().__init__(locale=locale, tick=False)
        self._legacy = QTimer(self)
        self._legacy.timeout.connect(self._legacy_tick)
        self._legacy.start(1000)

    def _legacy_tick(self) -> None:
        import time as _time
        from zaldros_shell.backend import format_clock
        self._time, self._date = format_clock(_time.localtime(), self._locale)
        self._sample_meters()          # emits `changed` unconditionally, as the old tick did
        # The old getter re-read /proc/meminfo on every binding evaluation; the tray and the Start
        # footer are two such bindings.
        for _ in range(2):
            model.memory_percent(self._proc_root)


def measure(mode: str, seconds: float, meters_open: bool) -> dict:
    application = QCoreApplication.instance() or QCoreApplication([])
    counters = Counters()
    counters.install()
    try:
        state = LegacyState() if mode == "legacy" else ShellState(tick=True)
        if mode != "legacy" and meters_open:
            state.setMetersActive(True)
        state.changed.connect(lambda: setattr(counters, "signals", counters.signals + 1))

        # Settle: the first construction touches /proc and loads fonts, which is start-up cost,
        # not idle cost.
        QTimer.singleShot(200, application.quit)
        application.exec()
        counters.proc_reads = 0
        counters.signals = 0
        before_cpu = cpu_seconds()
        before_voluntary, before_involuntary = context_switches()
        started = time.monotonic()

        QTimer.singleShot(int(seconds * 1000), application.quit)
        application.exec()

        elapsed = time.monotonic() - started
        after_voluntary, after_involuntary = context_switches()
        result = {
            "mode": mode,
            "meters_open": bool(meters_open),
            "elapsed_seconds": round(elapsed, 2),
            "cpu_seconds": round(cpu_seconds() - before_cpu, 4),
            "voluntary_ctx": after_voluntary - before_voluntary,
            "involuntary_ctx": after_involuntary - before_involuntary,
            "proc_reads": counters.proc_reads,
            "signals": counters.signals,
        }
        result["cpu_per_minute_ms"] = round(result["cpu_seconds"] / elapsed * 60 * 1000, 1)
        # Say what the numbers cannot say. A resolution limit reported as "0" is a false claim.
        tick_ms = 1000 / os.sysconf("SC_CLK_TCK")
        notes = []
        if result["cpu_seconds"] < tick_ms / 1000:
            notes.append(f"cpu_seconds is below this kernel's accounting resolution "
                         f"({tick_ms:.0f} ms): read it as '< {tick_ms:.0f} ms', not as zero")
        if result["voluntary_ctx"] == 0:
            notes.append("voluntary_ctx stayed 0: this kernel does not increment "
                         "voluntary_ctxt_switches (seen under gVisor) — the figure is unusable "
                         "here, use proc_reads and signals instead")
        result["notes"] = notes
        state.deleteLater()
        return result
    finally:
        counters.restore()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seconds", type=float, default=60.0)
    parser.add_argument("--mode", choices=["backend", "legacy", "both"], default="both")
    parser.add_argument("--meters", action="store_true",
                        help="measure with a meter surface open (the worst case, not the idle one)")
    parser.add_argument("--json", type=Path, help="also write the readings to this file")
    arguments = parser.parse_args()

    modes = ["legacy", "backend"] if arguments.mode == "both" else [arguments.mode]
    results = [measure(mode, arguments.seconds, arguments.meters) for mode in modes]

    width = max(len(key) for key in results[0])
    print(f"{'':<{width}}  " + "  ".join(f"{result['mode']:>12}" for result in results))
    for key in ("elapsed_seconds", "cpu_seconds", "cpu_per_minute_ms", "voluntary_ctx",
                "proc_reads", "signals"):
        print(f"{key:<{width}}  " + "  ".join(f"{result[key]:>12}" for result in results))

    if len(results) == 2:
        legacy, backend = results
        for key in ("cpu_seconds", "voluntary_ctx", "proc_reads", "signals"):
            if backend[key]:
                print(f"{key}: {legacy[key] / backend[key]:.1f}x less")
            elif legacy[key]:
                print(f"{key}: {legacy[key]} -> 0")

    for result in results:
        for note in result.get("notes", []):
            print(f"note ({result['mode']}): {note}")

    if arguments.json:
        arguments.json.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"written: {arguments.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
