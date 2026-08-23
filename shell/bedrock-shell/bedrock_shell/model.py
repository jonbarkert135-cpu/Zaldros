"""Qt-facing models. All logic lives in backend.py / desktop_entries.py / system.py so it stays
testable without Qt."""

from __future__ import annotations

import time

from PySide6.QtCore import (
    Property, QAbstractListModel, QModelIndex, QObject, Qt, QTimer, Signal, Slot,
)

from .backend import AppEntry, format_clock, load_pinned, memory_percent, read_running_commands
from .desktop_entries import DesktopApp, discover, launch
from . import system

NAME, EXEC, ICON, COLOR, RUNNING, INSTALLED, SUBTITLE = (Qt.UserRole + n for n in range(7))


class AppModel(QAbstractListModel):
    """Bedrock's default pin set, cross-checked against the machine's real application database.

    `installed` is real: it is true only when a matching .desktop entry exists on this system.
    Pins that are not installed are shown dimmed — never silently presented as available.
    """

    def __init__(self, entries: list[AppEntry] | None = None, proc_root: str = "/proc",
                 installed: list[DesktopApp] | None = None) -> None:
        super().__init__()
        self._entries = entries if entries is not None else load_pinned()
        self._proc_root = proc_root
        self._installed = installed if installed is not None else discover()
        self._by_exec = {app.exec_name: app for app in self._installed if app.exec_name}
        self._by_name = {app.name.casefold(): app for app in self._installed}
        self._running: set[str] = set()
        self.refresh()

    def roleNames(self) -> dict:  # noqa: N802 (Qt naming)
        return {NAME: b"name", EXEC: b"execName", ICON: b"icon", COLOR: b"color",
                RUNNING: b"running", INSTALLED: b"installed", SUBTITLE: b"subtitle"}

    def rowCount(self, parent=QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._entries)

    def _match(self, entry: AppEntry) -> DesktopApp | None:
        return self._by_exec.get(entry.exec_name) or self._by_name.get(entry.name.casefold())

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._entries):
            return None
        entry = self._entries[index.row()]
        match = self._match(entry)
        return {
            NAME: entry.name, EXEC: entry.exec_name, ICON: entry.icon, COLOR: entry.color,
            RUNNING: entry.exec_name in self._running,
            INSTALLED: match is not None,
            SUBTITLE: "" if match else "не установлено",
        }.get(role)

    @Slot(int, result=bool)
    def launchRow(self, row: int) -> bool:  # noqa: N802
        if not 0 <= row < len(self._entries):
            return False
        match = self._match(self._entries[row])
        return launch(match) if match else False

    @Slot()
    def refresh(self) -> None:
        self._running = read_running_commands(self._proc_root)
        if self._entries:
            top = self.index(0, 0)
            self.dataChanged.emit(top, self.index(len(self._entries) - 1, 0), [RUNNING])


class InstalledAppModel(QAbstractListModel):
    """Every application actually installed on this machine — the "All apps" list."""

    countChanged = Signal()

    def __init__(self, apps: list[DesktopApp] | None = None) -> None:
        super().__init__()
        self._apps = apps if apps is not None else discover()

    def roleNames(self) -> dict:  # noqa: N802
        return {NAME: b"name", EXEC: b"execName", ICON: b"icon", SUBTITLE: b"subtitle",
                COLOR: b"color"}

    def rowCount(self, parent=QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._apps)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._apps):
            return None
        app = self._apps[index.row()]
        palette = ["#3a7ebf", "#c95d2b", "#3f8f5f", "#8a5cc4", "#c1483f", "#2f8f96"]
        return {NAME: app.name, EXEC: app.exec_name, ICON: app.initial,
                SUBTITLE: app.comment[:60], COLOR: palette[index.row() % len(palette)]}.get(role)

    @Slot(int, result=bool)
    def launchRow(self, row: int) -> bool:  # noqa: N802
        return launch(self._apps[row]) if 0 <= row < len(self._apps) else False

    @Property(int, notify=countChanged)
    def count(self) -> int:
        return len(self._apps)


class SystemState(QObject):
    """Tray and quick-settings readouts. Every property has an `*Available` companion; when it is
    false the UI shows the reason instead of a number."""

    changed = Signal()

    def __init__(self, readings: dict | None = None) -> None:
        super().__init__()
        self._readings = readings if readings is not None else system.snapshot()

    @Slot()
    def refresh(self) -> None:
        self._readings = system.snapshot()
        self.changed.emit()

    def _value(self, key: str) -> int:
        reading = self._readings.get(key)
        return -1 if reading is None or reading.value is None else reading.value

    def _available(self, key: str) -> bool:
        reading = self._readings.get(key)
        return bool(reading and reading.available)

    def _detail(self, key: str) -> str:
        reading = self._readings.get(key)
        return reading.detail if reading else "нет данных"

    @Property(int, notify=changed)
    def batteryPercent(self) -> int:  # noqa: N802
        return self._value("battery")

    @Property(bool, notify=changed)
    def batteryAvailable(self) -> bool:  # noqa: N802
        return self._available("battery")

    @Property(str, notify=changed)
    def batteryDetail(self) -> str:  # noqa: N802
        return self._detail("battery")

    @Property(int, notify=changed)
    def brightnessPercent(self) -> int:  # noqa: N802
        return self._value("brightness")

    @Property(bool, notify=changed)
    def brightnessAvailable(self) -> bool:  # noqa: N802
        return self._available("brightness")

    @Property(int, notify=changed)
    def volumePercent(self) -> int:  # noqa: N802
        return self._value("volume")

    @Property(bool, notify=changed)
    def volumeAvailable(self) -> bool:  # noqa: N802
        return self._available("volume")

    @Property(str, notify=changed)
    def volumeDetail(self) -> str:  # noqa: N802
        return self._detail("volume")

    @Property(bool, notify=changed)
    def networkAvailable(self) -> bool:  # noqa: N802
        return self._available("network")

    @Property(str, notify=changed)
    def networkDetail(self) -> str:  # noqa: N802
        reading = self._readings.get("network")
        return reading.detail if reading else "нет данных"

    @Property(bool, notify=changed)
    def bluetoothAvailable(self) -> bool:  # noqa: N802
        return self._available("bluetooth")

    @Property(str, notify=changed)
    def bluetoothDetail(self) -> str:  # noqa: N802
        return self._detail("bluetooth")

    @Property(str, constant=True)
    def userName(self) -> str:  # noqa: N802
        return system.user_name()


class ShellState(QObject):
    """Clock, locale and honest system readouts for the shell chrome."""

    changed = Signal()

    def __init__(self, locale: str = "ru", proc_root: str = "/proc", tick: bool = True) -> None:
        super().__init__()
        self._locale = locale
        self._proc_root = proc_root
        self._time = ""
        self._date = ""
        self.update()
        if tick:
            self._timer = QTimer(self)
            self._timer.timeout.connect(self.update)
            self._timer.start(1000)

    @Slot()
    def update(self) -> None:
        self._time, self._date = format_clock(time.localtime(), self._locale)
        self.changed.emit()

    @Property(str, notify=changed)
    def timeText(self) -> str:  # noqa: N802
        return self._time

    @Property(str, notify=changed)
    def dateText(self) -> str:  # noqa: N802
        return self._date

    @Property(str, constant=True)
    def locale(self) -> str:
        return self._locale

    @Property(int, notify=changed)
    def memoryPercent(self) -> int:  # noqa: N802
        """-1 means 'not measurable here' — the UI must show a dash, not a fabricated number."""
        value = memory_percent(self._proc_root)
        return -1 if value is None else value
