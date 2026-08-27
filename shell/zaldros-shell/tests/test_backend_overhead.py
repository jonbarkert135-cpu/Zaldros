"""The polling is gone, and it must stay gone.

Before the backend the shell woke 86 400 times a day to redraw a clock that shows `HH:MM`, and
each of those wakeups also re-read /proc/stat and /proc/meminfo. These tests pin the three
properties that replaced it:

* the clock arms one single-shot timer aimed at the next minute boundary;
* the meters sample only while a surface that draws them is open;
* an idle shell runs no repeating timer at all.

The numbers themselves are measured by `tools/zaldros-bench/backend_overhead.py`; this file is the
regression guard, so a well-meaning `QTimer(1000)` cannot come back unnoticed.
"""

from __future__ import annotations

import time

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QCoreApplication, QTimer     # noqa: E402

from zaldros_shell.model import ShellState              # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QCoreApplication.instance() or QCoreApplication([])


def repeating_timers(owner) -> list[QTimer]:
    return [child for child in owner.findChildren(QTimer)
            if child.isActive() and not child.isSingleShot()]


def test_an_idle_shell_runs_no_repeating_timer(app):
    state = ShellState(tick=True)
    try:
        assert repeating_timers(state) == [], "something is polling again"
    finally:
        state.deleteLater()


def test_the_clock_is_armed_for_the_next_minute_not_for_one_second(app):
    state = ShellState(tick=True)
    try:
        timers = [child for child in state.findChildren(QTimer) if child.isActive()]
        assert len(timers) == 1
        clock = timers[0]
        assert clock.isSingleShot()
        remaining = clock.remainingTime()
        expected = (60 - time.time() % 60) * 1000
        assert 0 < remaining <= 60_020
        assert abs(remaining - expected) < 1500, (remaining, expected)
    finally:
        state.deleteLater()


def test_the_clock_only_notifies_when_the_displayed_text_changes(app):
    """The taskbar shows `HH:MM`. Emitting `changed` every second re-evaluates every binding in
    the tray to produce the same string."""
    state = ShellState(tick=False)
    seen = []
    state.changed.connect(lambda: seen.append(state.timeText))
    state.updateClock()
    state.updateClock()
    assert seen == [], "the minute has not changed, so nothing should have been announced"


def test_the_meters_run_only_while_a_surface_shows_them(app):
    state = ShellState(tick=False)
    try:
        assert not state.metersActive
        assert repeating_timers(state) == []

        state.setMetersActive(True)
        assert state.metersActive
        assert len(repeating_timers(state)) == 1
        assert repeating_timers(state)[0].interval() == ShellState.METER_INTERVAL_MS

        state.setMetersActive(False)
        assert not state.metersActive
        assert repeating_timers(state) == []
    finally:
        state.deleteLater()


def test_two_open_surfaces_keep_the_meters_running_until_the_last_one_closes(app):
    """Start's memory line and the game bar's performance widget can be open at once."""
    state = ShellState(tick=False)
    try:
        state.setMetersActive(True)
        state.setMetersActive(True)
        state.setMetersActive(False)
        assert state.metersActive, "the second surface is still open"
        state.setMetersActive(False)
        assert not state.metersActive
    finally:
        state.deleteLater()


def test_a_meter_shows_a_number_the_moment_its_surface_opens(app):
    """The old 1 Hz timer had always been running, so the meters were warm when a panel opened.

    CPU load is a difference between two samples: without a baseline taken at construction, the
    first second after Win+G would show «—» where Windows shows a number. This is that guard.
    """
    state = ShellState(tick=False)
    try:
        time.sleep(0.05)
        state.setMetersActive(True)
        assert state.cpuPercent >= 0, "the CPU meter would show a dash for a second"
        assert state.memoryPercent >= 0
    finally:
        state.deleteLater()


def test_reading_the_memory_property_does_not_open_a_file_per_binding(app, monkeypatch):
    """The getter used to read /proc/meminfo on every binding evaluation."""
    state = ShellState(tick=False)
    state.setMetersActive(True)
    reads = []
    monkeypatch.setattr("zaldros_shell.model.memory_percent",
                        lambda *_args: reads.append(1) or 42)
    for _ in range(20):
        _ = state.memoryPercent
    assert reads == [], "memoryPercent must serve the cached sample while the meters run"
