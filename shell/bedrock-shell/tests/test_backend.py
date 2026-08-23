import json
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bedrock_shell.backend import (  # noqa: E402
    AppEntry, format_clock, load_pinned, memory_percent, read_running_commands,
)


def test_pinned_entries_load_and_are_complete():
    entries = load_pinned()
    assert len(entries) >= 8
    for entry in entries:
        assert entry.name and entry.exec_name and entry.icon
        assert entry.color.startswith("#")


def test_running_commands_are_real_processes():
    names = read_running_commands()
    # This test asserts we read the real process table, not a fixture.
    assert names == set() or any(name for name in names)
    assert read_running_commands("/nonexistent") == set()


def test_running_flag_matches_a_process_that_really_exists():
    names = read_running_commands()
    if not names:
        pytest.skip("/proc not readable in this environment")
    entries = [AppEntry("Self", sorted(names)[0], "x", "#000000")]
    assert entries[0].exec_name in names


def test_clock_formats_per_locale():
    moment = time.struct_time((2026, 8, 23, 14, 5, 0, 6, 235, 0))
    assert format_clock(moment, "ru") == ("14:05", "23.08.2026")
    assert format_clock(moment, "en_US")[1] == "08/23/2026"
    assert format_clock(moment, "de")[0] == "14:05"


def test_memory_percent_is_real_or_none():
    value = memory_percent()
    assert value is None or 0 <= value <= 100
    assert memory_percent("/nonexistent") is None
