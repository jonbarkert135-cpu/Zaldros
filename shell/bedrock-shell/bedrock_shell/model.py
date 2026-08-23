"""Qt-facing models. Kept separate from `backend.py` so the logic is testable without Qt."""

from __future__ import annotations

import time

from PySide6.QtCore import (
    Property, QAbstractListModel, QModelIndex, QObject, Qt, QTimer, Signal, Slot,
)

from .backend import AppEntry, format_clock, load_pinned, memory_percent, read_running_commands

NAME, EXEC, ICON, COLOR, RUNNING = (Qt.UserRole + n for n in range(5))


class AppModel(QAbstractListModel):
    """Pinned applications plus a *real* running/not-running flag taken from /proc."""

    def __init__(self, entries: list[AppEntry] | None = None, proc_root: str = "/proc") -> None:
        super().__init__()
        self._entries = entries if entries is not None else load_pinned()
        self._proc_root = proc_root
        self._running: set[str] = set()
        self.refresh()

    def roleNames(self) -> dict:  # noqa: N802 (Qt naming)
        return {NAME: b"name", EXEC: b"execName", ICON: b"icon", COLOR: b"color",
                RUNNING: b"running"}

    def rowCount(self, parent=QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._entries)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._entries):
            return None
        entry = self._entries[index.row()]
        return {
            NAME: entry.name, EXEC: entry.exec_name, ICON: entry.icon, COLOR: entry.color,
            RUNNING: entry.exec_name in self._running,
        }.get(role)

    @Slot()
    def refresh(self) -> None:
        self._running = read_running_commands(self._proc_root)
        if self._entries:
            top = self.index(0, 0)
            self.dataChanged.emit(top, self.index(len(self._entries) - 1, 0), [RUNNING])


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
