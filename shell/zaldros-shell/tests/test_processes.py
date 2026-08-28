# SPDX-License-Identifier: GPL-3.0-or-later
"""The Task Manager's data layer, against a synthetic /proc and against this machine's real one.

A synthetic /proc is what makes the honesty rules testable: the CPU column of a first sample, a
process that vanishes mid-read, an unreadable /proc/<pid>/io. The live checks then prove the same
code reads a real kernel — a fixture that only ever sees a fake /proc proves nothing about Linux.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from zaldros_backend import processes
from zaldros_shell import taskmanager


def write_proc(root: Path, pid: int, name: str, utime: int = 0, rss_pages: int = 100,
               threads: int = 1, state: str = "S", cmdline: str = "/usr/bin/thing") -> None:
    base = root / str(pid)
    base.mkdir(parents=True, exist_ok=True)
    fields = ["0"] * 52
    fields[0] = state                      # field 3 of /proc/pid/stat, first after comm
    fields[1] = "1"                        # ppid
    fields[11] = str(utime)                # utime
    fields[12] = "0"                       # stime
    fields[17] = str(threads)
    fields[19] = "500"                     # starttime
    fields[21] = str(rss_pages)
    (base / "stat").write_text(f"{pid} ({name}) " + " ".join(fields))
    (base / "status").write_text(f"Name:\t{name}\nUid:\t{os.getuid()}\t{os.getuid()}\n")
    (base / "cmdline").write_text(cmdline.replace(" ", "\0") + "\0")


@pytest.fixture()
def proc(tmp_path: Path) -> Path:
    root = tmp_path / "proc"
    root.mkdir()
    (root / "stat").write_text("cpu  100 0 100 800 0 0 0 0 0 0\ncpu0 50 0 50 400 0 0 0 0 0 0\n"
                               "cpu1 50 0 50 400 0 0 0 0 0 0\n")
    (root / "meminfo").write_text("MemTotal: 8000000 kB\nMemAvailable: 4000000 kB\n"
                                  "SwapTotal: 1000000 kB\nSwapFree: 1000000 kB\n")
    (root / "uptime").write_text("1234.5 5678.9\n")
    (root / "diskstats").write_text(
        " 8 0 sda 1 0 200 0 0 0 400 0 0 0 0\n 8 1 sda1 1 0 999 0 0 0 999 0 0 0 0\n")
    (root / "net").mkdir()
    (root / "net" / "dev").write_text(
        "Inter-|   Receive\n face |bytes\n"
        "    lo: 9999 0 0 0 0 0 0 0 9999 0 0 0 0 0 0 0\n"
        "  eth0: 1000 0 0 0 0 0 0 0 2000 0 0 0 0 0 0 0\n")
    write_proc(root, 1, "init")
    write_proc(root, 42, "firefox", utime=100, rss_pages=1000, threads=8)
    return root


# --- reading ---------------------------------------------------------------------------------
def test_a_process_name_with_spaces_and_brackets_is_parsed_from_the_right_bracket(proc: Path):
    write_proc(proc, 77, "Web Content (tab)")
    found = processes.read_process(77, str(proc))
    assert found is not None and found.name == "Web Content (tab)"


def test_a_process_that_disappears_mid_read_is_none_not_an_exception(proc: Path):
    assert processes.read_process(999, str(proc)) is None


def test_the_first_sample_has_no_cpu_column_because_one_reading_cannot_be_a_load(proc: Path):
    sampler = processes.Sampler(str(proc), clock=lambda: 0.0)
    first = sampler.sample()
    assert first.processes and all(item.cpu is None for item in first.processes)
    assert first.cpu is None


def test_the_second_sample_turns_two_readings_into_a_percentage(proc: Path):
    ticks = iter([0.0, 1.0])
    sampler = processes.Sampler(str(proc), clock=lambda: next(ticks))
    sampler.sample()
    write_proc(proc, 42, "firefox", utime=100 + processes.CLOCK_TICKS // 2, rss_pages=1000,
               threads=8)
    second = sampler.sample()
    firefox = next(item for item in second.processes if item.pid == 42)
    assert firefox.cpu == pytest.approx(50.0, abs=1.0)


def test_memory_and_uptime_come_from_the_files_not_from_constants(proc: Path):
    snapshot = processes.Sampler(str(proc), clock=lambda: 0.0).sample()
    assert snapshot.memory_total == 8000000 * 1024
    assert snapshot.memory_percent == 50
    assert snapshot.uptime == 1234


def test_disk_counters_do_not_count_a_partition_inside_its_own_disk(proc: Path):
    read, written = processes.disk_counters(str(proc))
    assert read == 200 * 512 and written == 400 * 512


def test_loopback_traffic_is_not_network_traffic(proc: Path):
    assert processes.net_counters(str(proc)) == (1000, 2000)


def test_rates_are_unknown_until_there_are_two_samples(proc: Path):
    ticks = iter([0.0, 2.0])
    sampler = processes.Sampler(str(proc), clock=lambda: next(ticks))
    assert sampler.sample().disk_read_rate is None
    assert sampler.sample().disk_read_rate == 0.0


# --- acting ----------------------------------------------------------------------------------
def test_ending_a_process_that_is_gone_reports_what_the_kernel_said(proc: Path):
    facet = processes.ProcessFacet(str(proc))
    result = facet.end(999999)
    assert not result.available and "заверш" in result.detail


def test_init_is_never_signalled(proc: Path):
    assert not processes.ProcessFacet(str(proc)).end(1).available


def test_ending_a_real_child_actually_kills_it():
    import subprocess
    child = subprocess.Popen(["sleep", "30"])
    facet = processes.ProcessFacet()
    assert facet.alive(child.pid)
    assert facet.end(child.pid).available
    assert child.wait(timeout=5) is not None
    assert not facet.alive(child.pid)


# --- startup ---------------------------------------------------------------------------------
def test_autostart_entries_are_read_and_hidden_means_disabled(tmp_path: Path):
    directory = tmp_path / "autostart"
    directory.mkdir()
    (directory / "a.desktop").write_text("[Desktop Entry]\nName=Alpha\nExec=alpha\n")
    (directory / "b.desktop").write_text("[Desktop Entry]\nName=Beta\nExec=beta\nHidden=true\n")
    entries = processes.ProcessFacet().startup([str(directory)])
    assert [(entry.detail, entry.get("enabled")) for entry in entries] == [
        ("Alpha", True), ("Beta", False)]


def test_toggling_an_entry_writes_a_user_copy_and_the_read_back_shows_it(tmp_path, monkeypatch):
    system_dir = tmp_path / "xdg" / "autostart"
    system_dir.mkdir(parents=True)
    (system_dir / "a.desktop").write_text("[Desktop Entry]\nName=Alpha\nExec=alpha\n")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    facet = processes.ProcessFacet()
    result = facet.set_startup_enabled(str(system_dir / "a.desktop"), False)
    assert result.available
    user_copy = tmp_path / "config" / "autostart" / "a.desktop"
    assert "Hidden=true" in user_copy.read_text()
    entries = facet.startup([str(system_dir), str(user_copy.parent)])
    assert [entry.get("enabled") for entry in entries] == [False]   # the user copy wins


# --- formatting and sorting -------------------------------------------------------------------
def test_an_unknown_value_is_a_dash_never_a_zero():
    assert taskmanager.format_bytes(None) == taskmanager.DASH
    assert taskmanager.format_percent(None) == taskmanager.DASH
    assert taskmanager.format_rate(None) == taskmanager.DASH


def test_bytes_are_formatted_the_way_the_task_manager_does():
    assert taskmanager.format_bytes(1024) == "1,0 КБ"
    assert taskmanager.format_bytes(200 * 1024 ** 2) == "200 МБ"


def test_processes_with_an_unknown_cpu_never_displace_a_measured_one():
    rows = [{"cpu": None, "pid": 1}, {"cpu": 5.0, "pid": 2}, {"cpu": None, "pid": 3}]
    for descending in (True, False):
        ordered = taskmanager.sort_rows(rows, "cpu", descending)
        assert ordered[0]["pid"] == 2
        assert [row["pid"] for row in ordered[1:]] == [1, 3]


def test_search_matches_name_command_line_and_exact_pid():
    row = {"name": "firefox", "cmdline": "/usr/lib/firefox --tab", "pid": 42}
    assert taskmanager.matches(row, "fire") and taskmanager.matches(row, "--tab")
    assert taskmanager.matches(row, "42") and not taskmanager.matches(row, "4")


def test_sorting_by_an_unknown_column_is_refused_rather_than_silently_ignored():
    with pytest.raises(ValueError):
        taskmanager.sort_rows([], "nonsense")


def test_uptime_uses_the_windows_shape():
    assert taskmanager.format_uptime(90061) == "1:01:01:01"


def test_a_gap_in_measurement_draws_as_a_gap_not_as_zero():
    history = taskmanager.History(size=3)
    for value in (10.0, None, 30.0, 40.0):
        history.push(value)
    assert history.values == [None, 30.0, 40.0]
    assert history.points() == [30.0, 40.0]


# --- the real machine --------------------------------------------------------------------------
def test_this_machine_really_has_processes_and_they_are_ours_to_read():
    facet = processes.ProcessFacet()
    snapshot = facet.sample()
    assert len(snapshot.processes) >= 1
    mine = next(item for item in snapshot.processes if item.pid == os.getpid())
    assert mine.rss > 0 and mine.threads >= 1 and mine.user


def test_grouping_without_a_compositor_says_so_instead_of_inventing_applications():
    facet = processes.ProcessFacet()
    grouped = facet.group(facet.sample())
    assert grouped["apps"] == [] and not grouped["apps_available"]
    assert grouped["apps_reason"]


def test_a_gpu_that_does_not_report_load_is_listed_with_a_reason_not_with_a_number(tmp_path):
    card = tmp_path / "card0" / "device"
    card.mkdir(parents=True)
    (card / "vendor").write_text("0x10de\n")
    cards = processes.gpus(str(tmp_path))
    assert len(cards) == 1 and not cards[0].available
    assert cards[0].percent == -1 and cards[0].get("reason")


# --- the Qt model: the window decides when the machine is read ---------------------------------
class CountingFacet(processes.ProcessFacet):
    """Counts samples, so 'no background polling' is a test rather than a promise."""

    def __init__(self, root: str) -> None:
        super().__init__(root)
        self.samples = 0

    def sample(self, with_io: bool = False):
        self.samples += 1
        return super().sample(with_io=with_io)


def test_a_closed_task_manager_reads_nothing_at_all(proc: Path, qt_app):
    from zaldros_shell.model import ProcessModel
    facet = CountingFacet(str(proc))
    model = ProcessModel(facet, interval_ms=10)
    assert facet.samples == 0
    model.setActive(True)
    assert facet.samples == 1          # opening the window is the only trigger
    model.setActive(False)
    before = facet.samples
    qt_app.processEvents()
    assert facet.samples == before     # closed: the timer is stopped, nothing is read


def test_the_model_sorts_searches_and_reports_a_summary(proc: Path, qt_app):
    from zaldros_shell.model import ProcessModel
    model = ProcessModel(processes.ProcessFacet(str(proc)))
    model.refresh()
    assert model.count == 2
    model.search("firefox")
    assert model.count == 1
    model.search("")
    model.sortBy("pid")
    first = model.data(model.index(0, 0), [role for name, role in
                                           __import__("zaldros_shell.model", fromlist=["x"])
                                           .PROC_ROLES.items() if name == "pid"][0])
    assert first == 42                 # numeric columns start heaviest-first
    assert model.summary["processes"] == 2
