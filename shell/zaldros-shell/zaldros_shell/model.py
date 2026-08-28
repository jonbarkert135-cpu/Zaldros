"""Qt-facing models. All logic lives in backend.py / desktop_entries.py / system.py so it stays
testable without Qt."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

from PySide6.QtCore import (
    Property, QAbstractListModel, QModelIndex, QObject, Qt, QTimer, QUrl, Signal, Slot,
)
from PySide6.QtGui import QGuiApplication, QImage

from .backend import (AppEntry, cpu_percent, cpu_times, format_clock, load_pinned,
                      memory_percent, read_running_commands)
from .desktop_entries import DesktopApp, discover, launch
from . import clipboard as clipboard_history
from . import capture, portal
from . import files, hostinfo, prefs, settingscontrols, settingspages, system, taskmanager, weather

NAME, EXEC, ICON, COLOR, RUNNING, INSTALLED, SUBTITLE = (Qt.UserRole + n for n in range(7))

_BRIDGE = None


def _connect_backend(owner, domains, callback):
    """Wire one Qt object to the shared backend's change signal.

    One bridge per process, not one per model: the bridge owns the socket notifiers and the
    debounce timer, and a second one would mean the same D-Bus signal being handled twice.
    Returns None when Qt cannot watch the bus (no bus at all, or an offscreen render), and the
    model then simply keeps the readings it was built with — which is what the shell did before
    this existed, so nothing can be worse than it was.
    """
    global _BRIDGE
    try:
        from zaldros_backend.qtbridge import BackendBridge
    except Exception:                                  # noqa: BLE001 - reported, never fatal
        return None
    backend = system.backend()
    if not (backend.system_bus.available or backend.session_bus.available):
        return None
    if _BRIDGE is None:
        try:
            _BRIDGE = BackendBridge(backend)
        except Exception as exc:                       # noqa: BLE001 - shown, never swallowed
            print(f"backend bridge unavailable: {exc}", flush=True)
            return None
    wanted = set(domains)
    _BRIDGE.changed.connect(lambda domain: callback() if domain in wanted else None)
    return _BRIDGE


class AppModel(QAbstractListModel):
    """Zaldros's default pin set, cross-checked against the machine's real application database.

    `installed` is real: it is true only when a matching .desktop entry exists on this system.
    Pins that are not installed are shown dimmed — never silently presented as available.
    """

    barChanged = Signal()

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
            NAME: entry.name, EXEC: entry.exec_name, COLOR: entry.color,
            ICON: match.icon if (match and match.icon) else entry.exec_name,
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

    @Property("QVariantList", notify=barChanged)
    def taskbarPins(self) -> list:  # noqa: N802
        """The pins Windows 11 keeps on the bar itself. Start still shows the whole set."""
        rows = []
        for row, entry in enumerate(self._entries):
            if not entry.taskbar:
                continue
            match = self._match(entry)
            rows.append({
                "row": row,
                "name": entry.name,
                "color": entry.color,
                "icon": match.icon if (match and match.icon) else entry.exec_name,
                "running": entry.exec_name in self._running,
                "installed": match is not None,
            })
        return rows

    @Slot()
    def refresh(self) -> None:
        self._running = read_running_commands(self._proc_root)
        self.barChanged.emit()
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
        return {NAME: app.name, EXEC: app.exec_name, ICON: app.icon,
                SUBTITLE: app.comment[:60], COLOR: palette[index.row() % len(palette)]}.get(role)

    @Slot(int, result=bool)
    def launchRow(self, row: int) -> bool:  # noqa: N802
        return launch(self._apps[row]) if 0 <= row < len(self._apps) else False

    @Property(int, notify=countChanged)
    def count(self) -> int:
        return len(self._apps)


class SystemState(QObject):
    """Tray and quick-settings readouts. Every property has an `*Available` companion; when it is
    false the UI shows the reason instead of a number.

    The properties below are unchanged — the same names, the same types, the same wording for an
    absent value — because the taskbar and quick-settings QML must render pixel-for-pixel what it
    rendered before. What changed is underneath: instead of one snapshot taken at construction and
    never taken again, the readings are refreshed when UPower, NetworkManager or BlueZ *say* they
    changed. The tray used to freeze at its start-up values; now it does not, and it still costs
    nothing while nothing happens.
    """

    changed = Signal()

    def __init__(self, readings: dict | None = None, live: bool = True) -> None:
        super().__init__()
        self._readings = readings if readings is not None else system.snapshot()
        self._bridge = None
        if live and readings is None:
            self._bridge = _connect_backend(self, ("power", "network", "bluetooth", "audio"),
                                            self.refresh)

    @Slot()
    def refresh(self) -> None:
        self._readings = system.snapshot()
        self.changed.emit()

    # -- actions the tiles perform ------------------------------------------------------------
    # Quick settings could only *display* before this: the tiles had nothing behind them. These
    # go through the backend, so a click reaches NetworkManager, BlueZ or PipeWire and the result
    # comes back through the same change signal as any other update.
    @Slot(result=bool)
    def toggleWifi(self) -> bool:  # noqa: N802
        current = self._readings.get("network")
        enabled = bool(current and current.get("wifi_enabled"))
        result = system.backend().network.set_wifi_enabled(not enabled)
        self.refresh()
        return bool(result.ok)

    @Slot(result=bool)
    def toggleBluetooth(self) -> bool:  # noqa: N802
        current = self._readings.get("bluetooth")
        powered = bool(current and current.get("powered"))
        result = system.backend().bluetooth.set_powered(not powered)
        self.refresh()
        return bool(result.ok)

    @Slot(int, result=bool)
    def setVolume(self, percent: int) -> bool:  # noqa: N802
        result = system.backend().audio.set_volume(int(percent))
        self.refresh()
        return bool(result.ok)

    @Slot(result=bool)
    def toggleMute(self) -> bool:  # noqa: N802
        result = system.backend().audio.toggle_muted()
        self.refresh()
        return bool(result.ok)

    @Slot(int, result=bool)
    def setBrightness(self, percent: int) -> bool:  # noqa: N802
        result = system.backend().display.set_brightness(int(percent))
        self.refresh()
        return bool(result.ok)

    @Property(bool, notify=changed)
    def brightnessWritable(self) -> bool:  # noqa: N802
        """False on a machine where the backlight can be read but not written — the slider is
        then shown at its real value and disabled, instead of moving and doing nothing."""
        reading = self._readings.get("brightness")
        return bool(reading and reading.available and reading.get("writable"))

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

    @Property(str, notify=changed)
    def keyboardLayout(self) -> str:  # noqa: N802
        """Tray layout badge. Empty when nothing reported one, so the tray shows no badge."""
        reading = self._readings.get("keyboard")
        return reading.detail if reading and reading.available else ""

    @Property(str, notify=changed)
    def keyboardDetail(self) -> str:  # noqa: N802
        return self._detail("keyboard")

    @Slot(result=bool)
    def switchLayout(self) -> bool:  # noqa: N802
        """Clicking the tray badge moves to the next layout, as it does in Windows. KWin owns the
        keyboard on Wayland, so KWin is asked; if it does not answer, nothing pretends to happen."""
        switched = system.switch_layout()
        if switched:
            self.refresh()
        return switched

    @Property(str, constant=True)
    def userName(self) -> str:  # noqa: N802
        return system.user_name()


class ShellState(QObject):
    """Clock, locale and honest system readouts for the shell chrome.

    The clock used to tick once a second and drag the CPU and memory meters along with it: every
    tick re-read /proc/stat, and every `changed` made QML re-evaluate `memoryPercent`, whose
    getter re-read /proc/meminfo. 86 400 wakeups a day to move a display that shows `HH:MM`.

    Now the clock wakes on the minute boundary it actually needs — one single-shot timer, re-armed
    to the exact millisecond of the next minute, so it neither drifts nor fires twice — and the
    meters run only while a surface that draws them is open (`setMetersActive`). Measured
    difference: `tools/zaldros-bench/backend_overhead.py`.
    """

    changed = Signal()

    METER_INTERVAL_MS = 1000

    def __init__(self, locale: str = "ru", proc_root: str = "/proc", tick: bool = True) -> None:
        super().__init__()
        self._locale = locale
        self._proc_root = proc_root
        self._time = ""
        self._date = ""
        self._cpu_previous = None
        # One baseline reading at construction. CPU load is a difference between two samples, so
        # without it the first second after a meter surface opens would show «—» where the old
        # always-on 1 Hz timer showed a number. One /proc/stat read at start-up buys that back.
        self._cpu_current = cpu_times(proc_root)
        self._cpu = -1
        self._memory = -1
        self._meters = 0
        self._clock_timer: QTimer | None = None
        self._meter_timer: QTimer | None = None
        self.updateClock()
        if tick:
            self._clock_timer = QTimer(self)
            self._clock_timer.setSingleShot(True)
            self._clock_timer.timeout.connect(self._clock_tick)
            self._arm_clock()

    # -- clock -------------------------------------------------------------------------------
    def _arm_clock(self) -> None:
        if self._clock_timer is None:
            return
        now = time.time()
        self._clock_timer.start(max(1, int((60 - now % 60) * 1000) + 20))

    def _clock_tick(self) -> None:
        self.updateClock()
        self._arm_clock()

    @Slot()
    def updateClock(self) -> None:  # noqa: N802
        text, date = format_clock(time.localtime(), self._locale)
        if (text, date) != (self._time, self._date):
            self._time, self._date = text, date
            self.changed.emit()

    @Slot()
    def update(self) -> None:
        """Everything at once. Kept for callers that want a full refresh on demand."""
        self.updateClock()
        self._sample_meters()

    # -- meters ------------------------------------------------------------------------------
    @Slot(bool)
    def setMetersActive(self, active: bool) -> None:  # noqa: N802
        """A surface that shows the CPU/memory meters says when it is open.

        Reference-counted, because two can be open at once (Start's memory line and the game
        bar's performance widget), and the meters must keep running until the last one closes.
        """
        self._meters = max(0, self._meters + (1 if active else -1))
        if self._meters > 0:
            if self._meter_timer is None:
                self._meter_timer = QTimer(self)
                self._meter_timer.timeout.connect(self._sample_meters)
            self._sample_meters()
            if not self._meter_timer.isActive():
                self._meter_timer.start(self.METER_INTERVAL_MS)
        elif self._meter_timer is not None:
            self._meter_timer.stop()

    @property
    def metersActive(self) -> bool:  # noqa: N802
        return self._meters > 0

    def _sample_meters(self) -> None:
        self._cpu_previous, self._cpu_current = self._cpu_current, cpu_times(self._proc_root)
        measured = cpu_percent(self._cpu_previous, self._cpu_current)
        memory = memory_percent(self._proc_root)
        self._cpu = -1 if measured is None else measured
        self._memory = -1 if memory is None else memory
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
    def cpuPercent(self) -> int:  # noqa: N802
        """Load between the last two ticks. -1 until two readings exist, or if /proc is unreadable."""
        return self._cpu

    @Property(int, notify=changed)
    def memoryPercent(self) -> int:  # noqa: N802
        """-1 means 'not measurable here' — the UI must show a dash, not a fabricated number.

        Reads the cached sample rather than /proc/meminfo. The getter used to open the file on
        every binding evaluation, which meant once per second per visible meter whether or not
        the panel was on screen.
        """
        if self._memory >= 0 or self._meters > 0:
            return self._memory
        value = memory_percent(self._proc_root)
        return -1 if value is None else value


NAME_R, PATH_R, KIND_R, SIZE_R, MODIFIED_R, GLYPH_R, ISDIR_R, SUB_R = (
    Qt.UserRole + 20 + n for n in range(8))


class FileModel(QAbstractListModel):
    """The contents of one directory on this machine — the Explorer list.

    Navigation is real: `openRow` descends into folders, `goUp` walks to the parent, `navigate`
    jumps to a path. A directory that cannot be read leaves the list empty and sets `errorText`.
    """

    changed = Signal()

    def __init__(self, path: str | None = None) -> None:
        super().__init__()
        self._path = str(Path(path) if path else Path.home())
        self._entries: list[files.Entry] = []
        self._error = ""
        self._history: list[str] = []
        self._forward: list[str] = []
        self.reload()

    def roleNames(self) -> dict:  # noqa: N802
        return {NAME_R: b"name", PATH_R: b"path", KIND_R: b"kind", SIZE_R: b"size",
                MODIFIED_R: b"modified", GLYPH_R: b"glyph", ISDIR_R: b"isDir"}

    def rowCount(self, parent=QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._entries)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._entries):
            return None
        entry = self._entries[index.row()]
        return {NAME_R: entry.name, PATH_R: entry.path, KIND_R: entry.kind,
                SIZE_R: files.human_size(entry.size, entry.is_dir),
                MODIFIED_R: files.format_modified(entry.modified),
                GLYPH_R: entry.glyph, ISDIR_R: entry.is_dir}.get(role)

    @Slot()
    def reload(self) -> None:
        self.beginResetModel()
        try:
            self._entries = files.list_directory(self._path)
            self._error = ""
        except OSError as exc:
            self._entries = []
            self._error = f"Не удалось открыть папку: {exc.strerror or exc}"
        self.endResetModel()
        self.changed.emit()

    @Slot(str)
    def navigate(self, path: str) -> None:
        if not Path(path).is_dir():
            self._error = "Папка недоступна"
            self.changed.emit()
            return
        self._history.append(self._path)
        self._forward.clear()
        self._path = str(Path(path))
        self.reload()

    @Slot(int)
    def openRow(self, row: int) -> None:  # noqa: N802
        """Double-click: a folder is entered, a file is handed to the desktop's default
        application, exactly as in Explorer."""
        if not 0 <= row < len(self._entries):
            return
        entry = self._entries[row]
        if entry.is_dir:
            self.navigate(entry.path)
            return
        self._apply(files.open_with_default_application(entry.path), reload=False)

    # --- operations on the real filesystem --------------------------------------------------
    # Each one reports its outcome in `errorText`; nothing is overwritten and nothing is deleted
    # outright (see files.move_to_trash).

    def _apply(self, result: files.Result, reload: bool = True) -> str:
        self._error = "" if result.ok else result.error
        if result.ok and reload:
            self.reload()
        else:
            self.changed.emit()
        return result.path if result.ok else ""

    @Slot(result=str)
    def createFolder(self) -> str:  # noqa: N802
        """Create "Новая папка" here and return its path so the view can select and rename it."""
        return self._apply(files.create_folder(self._path))

    @Slot(int, str, result=bool)
    def renameRow(self, row: int, new_name: str) -> bool:  # noqa: N802
        if not 0 <= row < len(self._entries):
            return False
        return bool(self._apply(files.rename(self._entries[row].path, new_name)))

    @Slot(int, result=bool)
    def deleteRow(self, row: int) -> bool:  # noqa: N802
        """Delete to the freedesktop bin, the way Windows deletes to the Recycle Bin."""
        if not 0 <= row < len(self._entries):
            return False
        return bool(self._apply(files.move_to_trash(self._entries[row].path)))

    @Slot(str, result=int)
    def rowForPath(self, path: str) -> int:  # noqa: N802
        """Row index of a path in the current listing, or -1. Used to select a folder we just
        created."""
        for index, entry in enumerate(self._entries):
            if entry.path == path:
                return index
        return -1

    @Slot()
    def goUp(self) -> None:  # noqa: N802
        parent = str(Path(self._path).parent)
        if parent != self._path:
            self.navigate(parent)

    @Slot()
    def goBack(self) -> None:  # noqa: N802
        if self._history:
            self._forward.append(self._path)
            self._path = self._history.pop()
            self.reload()

    @Slot()
    def goForward(self) -> None:  # noqa: N802
        if self._forward:
            self._history.append(self._path)
            self._path = self._forward.pop()
            self.reload()

    @Property(str, notify=changed)
    def path(self) -> str:
        return self._path

    @Property(str, notify=changed)
    def errorText(self) -> str:  # noqa: N802
        return self._error

    @Property(int, notify=changed)
    def count(self) -> int:
        return len(self._entries)

    @Property(bool, notify=changed)
    def canGoBack(self) -> bool:  # noqa: N802
        return bool(self._history)

    @Property(bool, notify=changed)
    def canGoForward(self) -> bool:  # noqa: N802
        return bool(self._forward)

    @Property("QVariantList", notify=changed)
    def breadcrumbs(self) -> list:
        """[{name, path}] from the filesystem root to the current directory."""
        parts = Path(self._path).parts
        crumbs = []
        for index in range(len(parts)):
            path = str(Path(*parts[: index + 1]))
            crumbs.append({"name": parts[index].strip("/") or "Этот компьютер", "path": path})
        return crumbs

    @Property("QVariantList", constant=True)
    def shortcuts(self) -> list:
        return [{"name": name, "path": path, "icon": icon}
                for name, path, icon in files.quick_access()]


class RecentModel(QAbstractListModel):
    """Recently modified files under the home directory — the Start panel's recommendations."""

    changed = Signal()

    def __init__(self, home: str | None = None, limit: int = 6,
                 switches: dict[str, bool] | None = None) -> None:
        super().__init__()
        # "Журнал действий → Недавние файлы" in Settings is this list. Off means the list is not
        # built at all — not built and hidden, which would still have walked the home directory.
        values = switches if switches is not None else prefs.load()
        self._entries = (files.recent_files(home, limit)
                         if values.get("privacy.recent_files", True) else [])

    def roleNames(self) -> dict:  # noqa: N802
        return {NAME_R: b"name", PATH_R: b"path", GLYPH_R: b"glyph", SUB_R: b"subtitle"}

    def rowCount(self, parent=QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._entries)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._entries):
            return None
        entry = self._entries[index.row()]
        return {NAME_R: entry.name, PATH_R: entry.path, GLYPH_R: entry.glyph,
                SUB_R: files.format_modified(entry.modified)}.get(role)

    @Property(int, notify=changed)
    def count(self) -> int:
        return len(self._entries)


class HostInfo(QObject):
    """Real machine facts for the Settings application (hostinfo.py)."""

    changed = Signal()

    def __init__(self, readings: dict[str, str] | None = None) -> None:
        super().__init__()
        self._data = readings if readings is not None else hostinfo.snapshot()

    @Slot()
    def refresh(self) -> None:
        self._data = hostinfo.snapshot()
        self.changed.emit()

    @Slot(str, result=str)
    def value(self, key: str) -> str:
        """Empty string means 'not measurable here' — Settings then shows a dash."""
        return self._data.get(key, "")

    @Property("QVariantMap", notify=changed)
    def all(self) -> dict:
        return dict(self._data)


class WeatherState(QObject):
    """The taskbar weather widget. Empty until a real reading arrives (weather.py)."""

    changed = Signal()

    def __init__(self, reading: "weather.Reading | None" = None, fetch: bool = True) -> None:
        super().__init__()
        self._reading = reading or weather.UNAVAILABLE
        if reading is None and fetch:
            weather.fetch_async(self._apply)

    def _apply(self, reading: "weather.Reading") -> None:
        # Called from the worker thread: only touch the attribute and emit, Qt queues the rest.
        self._reading = reading
        self.changed.emit()

    @Property(bool, notify=changed)
    def available(self) -> bool:
        return self._reading.available

    @Property(str, notify=changed)
    def temperature(self) -> str:
        return self._reading.temperature

    @Property(str, notify=changed)
    def condition(self) -> str:
        return self._reading.condition

    @Property(str, notify=changed)
    def place(self) -> str:
        return self._reading.place

    @Property(str, notify=changed)
    def glyph(self) -> str:
        return self._reading.glyph

    @Property(str, notify=changed)
    def detail(self) -> str:
        return self._reading.detail


class SettingsControls(QObject):
    """The bridge between a Settings row and the machine (settingscontrols.py).

    QML calls `activate(id)` when a row is clicked and gets back the state that was *read from the
    system afterwards*. Nothing is cached here: a switch that the service refused stays where the
    service left it, and the row redraws with the reason.
    """

    changed = Signal()

    def __init__(self, registry=None, home: Path | None = None) -> None:
        super().__init__()
        self._home = home
        self._registry = registry

    @property
    def registry(self):
        if self._registry is None:
            self._registry = settingscontrols.Registry(home=self._home)
        return self._registry

    @Slot()
    def refresh(self) -> None:
        """Rebuild: monitors, drives and user accounts appear and disappear."""
        self._registry = settingscontrols.Registry(home=self._home)
        self.changed.emit()

    @Slot(str, result="QVariantMap")
    def state(self, control_id: str) -> dict:
        return self.registry.state(control_id).as_variant()

    @Slot(str, result="QVariantMap")
    def activate(self, control_id: str) -> dict:
        """Click on a row: a switch flips, an action runs, anything else is only read back."""
        registry = self.registry
        state = registry.state(control_id)
        if state.kind == settingscontrols.SWITCH:
            state = registry.toggle(control_id)
        elif state.kind == settingscontrols.ACTION:
            state = registry.invoke(control_id)
        self.changed.emit()
        return state.as_variant()

    @Slot(str, "QVariant", result="QVariantMap")
    def set(self, control_id: str, value) -> dict:
        state = self.registry.set(control_id, value)
        self.changed.emit()
        return state.as_variant()

    @Slot(str, result="QVariantList")
    def choices(self, control_id: str) -> list:
        return list(self.registry.state(control_id).choices)


class SettingsTree(QObject):
    """The Settings information architecture (settingspages.py) as plain data for QML."""

    changed = Signal()

    def __init__(self, pages: dict | None = None, controls=None) -> None:
        super().__init__()
        self._controls = controls
        self._pages = (pages if pages is not None
                       else settingspages.to_variant(settingspages.build(controls=self._registry())))

    def _registry(self):
        return self._controls.registry if self._controls is not None else None

    @Slot()
    def refresh(self) -> None:
        self._pages = settingspages.to_variant(settingspages.build(controls=self._registry()))
        self.changed.emit()

    @Slot(str, result="QVariantMap")
    def page(self, page_id: str) -> dict:
        """A page of the tree — or, for `choice:<control>`, the option list built on the spot.

        Windows opens a dropdown here. Zaldros opens a page of the same cards with a mark on the
        current option: one visual language, no second widget, and every option is a real write.
        """
        if page_id.startswith("choice:"):
            return self._choice_page(page_id.split(":", 1)[1])
        return self._pages.get(page_id, {"id": page_id, "title": "", "parent": "", "entries": []})

    def _choice_page(self, control_id: str) -> dict:
        registry = self._registry()
        if registry is None:
            return {"id": f"choice:{control_id}", "title": "", "parent": "", "entries": []}
        control = registry.get(control_id)
        state = registry.state(control_id)
        entries = [{"title": option.get("title", ""), "subtitle": "", "glyph": "settings",
                    "value": "выбрано" if str(option.get("id")) == str(state.value) else "",
                    "group": "", "page": "", "url": "", "hasToggle": False, "toggle": False,
                    "pref": "", "control": control_id, "kind": "option",
                    "writable": state.writable, "reason": state.reason,
                    "option": str(option.get("id", ""))}
                   for option in state.choices]
        if not entries:
            entries = [{"title": state.reason or "нет вариантов", "subtitle": "", "glyph": "info",
                        "value": "", "group": "", "page": "", "url": "", "hasToggle": False,
                        "toggle": False, "pref": "", "control": "", "kind": "info",
                        "writable": False, "reason": state.reason, "option": ""}]
        return {"id": f"choice:{control_id}", "title": control.title if control else control_id,
                "glyph": "settings", "parent": "", "entries": entries}

    @Property("QVariantList", notify=changed)
    def rail(self) -> list:
        return [{"id": pid, "title": self._pages[pid]["title"], "glyph": self._pages[pid]["glyph"]}
                for pid in settingspages.RAIL if pid in self._pages]

    @Property(str, constant=True)
    def helpUrl(self) -> str:  # noqa: N802
        return settingspages.HELP_URL


class Prefs(QObject):
    """The switches that really switch something, backed by prefs.py.

    QML reads them as one map (`prefs.values["taskbar.search"]`) and writes with `prefs.set(...)`.
    A write that names an unimplemented key returns false instead of pretending to store it.
    """

    changed = Signal()

    def __init__(self, home: Path | None = None) -> None:
        super().__init__()
        self._home = home
        self._values = prefs.load(home)

    @Slot(str, result=bool)
    def value(self, key: str) -> bool:
        return bool(self._values.get(key, prefs.DEFAULTS.get(key, False)))

    @Slot(str, bool, result=bool)
    def set(self, key: str, value: bool) -> bool:
        if not prefs.set_value(key, value, self._home):
            return False
        self._values = prefs.load(self._home)
        self.changed.emit()
        return True

    @Slot(str, result=bool)
    def toggle(self, key: str) -> bool:
        return self.set(key, not self.value(key))

    @Slot()
    def refresh(self) -> None:
        self._values = prefs.load(self._home)
        self.changed.emit()

    @Property("QVariantMap", notify=changed)
    def values(self) -> dict:
        return dict(self._values)


CLIP_KIND, CLIP_PREVIEW, CLIP_PINNED, CLIP_PATH, CLIP_WHEN = (Qt.UserRole + 40 + n for n in range(5))


class ClipboardModel(QAbstractListModel):
    """Win+V: the real clipboard, not a mock-up.

    The model listens to QClipboard::dataChanged, so what the flyout lists is exactly what was
    copied in this session — text as text, an image as a PNG written into the session cache with
    the path kept here. Activating a row puts the entry *back* on the clipboard, which is the only
    thing the Windows flyout does when a card is clicked (it then pastes into the focused window;
    pasting for the user is not ours to do without a focused text field).
    """

    changed = Signal()

    def __init__(self, home=None, cache: Path | None = None, clipboard=None) -> None:
        super().__init__()
        self._home = home
        self._history = clipboard_history.History(home=home)
        self._cache = Path(cache) if cache else Path(
            os.environ.get("XDG_CACHE_HOME") or (Path.home() / ".cache")) / "zaldros" / "clipboard"
        self._clip = clipboard
        if self._clip is None:
            app = QGuiApplication.instance()
            self._clip = app.clipboard() if app is not None else None
        if self._clip is not None:
            self._clip.dataChanged.connect(self.capture)
            self.capture()

    # --- Qt model ---------------------------------------------------------------------------
    def roleNames(self) -> dict:  # noqa: N802
        return {CLIP_KIND: b"kind", CLIP_PREVIEW: b"preview", CLIP_PINNED: b"pinned",
                CLIP_PATH: b"path", CLIP_WHEN: b"when"}

    def rowCount(self, parent=QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._history)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._history):
            return None
        entry = self._history[index.row()]
        return {CLIP_KIND: entry.kind, CLIP_PREVIEW: entry.preview(), CLIP_PINNED: entry.pinned,
                CLIP_PATH: QUrl.fromLocalFile(entry.path).toString() if entry.path else "",
                CLIP_WHEN: time.strftime("%H:%M", time.localtime(entry.when))}.get(role)

    # --- clipboard --------------------------------------------------------------------------
    @Slot()
    def capture(self) -> bool:
        """Take whatever is on the clipboard now. Returns True when the history changed.

        With «Журнал буфера обмена» off in Settings nothing is recorded — the copy still works,
        Win+V simply has nothing to show, which is what that switch means.
        """
        if self._clip is None:
            return False
        if not prefs.load(self._home).get("clipboard.history", True):
            return False
        added = False
        text = self._clip.text()
        if text:
            added = self._history.add_text(text)
        else:
            image = self._clip.image()
            if image is not None and not image.isNull():
                self._cache.mkdir(parents=True, exist_ok=True)
                target = self._cache / f"clip-{int(time.time() * 1000)}.png"
                if image.save(str(target), "PNG"):
                    added = self._history.add_image(str(target))
        if added:
            self._refresh()
        return added

    def _refresh(self) -> None:
        self.beginResetModel()
        self.endResetModel()
        self.changed.emit()

    @Slot(int, result=bool)
    def applyRow(self, row: int) -> bool:  # noqa: N802
        """Put the entry back on the clipboard, ready to be pasted."""
        if self._clip is None or not 0 <= row < len(self._history):
            return False
        entry = self._history[row]
        if entry.kind == "text":
            self._clip.setText(entry.text)
        else:
            image = QImage(entry.path)
            if image.isNull():
                return False
            self._clip.setImage(image)
        return True

    @Slot(int, result=bool)
    def pinRow(self, row: int) -> bool:  # noqa: N802
        if self._history.toggle_pin(row):
            self._refresh()
            return True
        return False

    @Slot(int, result=bool)
    def deleteRow(self, row: int) -> bool:  # noqa: N802
        if self._history.remove(row):
            self._refresh()
            return True
        return False

    @Slot(result=int)
    def clearAll(self) -> int:  # noqa: N802
        """"Очистить все": everything except the pinned entries, as in Windows 11."""
        removed = self._history.clear()
        if removed:
            self._refresh()
        return removed

    @Property(bool, notify=changed)
    def empty(self) -> bool:
        return len(self._history) == 0


class GameBarModel(QObject):
    """Win+G: a capture panel that only offers what this machine can really do.

    Windows' game bar shows the same four tiles everywhere and lets you press ones that silently
    fail. Here each capability is resolved to an executable that exists (`capture.pick`), and when
    none does, `status` carries the sentence explaining what is missing — the tile is disabled and
    says why, which is the whole difference between a desktop and a screenshot of one.

    Screenshots are taken by the first available grabber and are only reported as taken when the
    file is on disk. Recording needs the compositor's permission: the PipeWire node comes from
    xdg-desktop-portal's ScreenCast (portal.py) and is fed to ffmpeg.
    """

    changed = Signal()

    def __init__(self, home=None, runner=None, clock=time.time) -> None:
        super().__init__()
        self._home = home
        self._run = runner or subprocess.Popen
        self._clock = clock
        self._recording_process = None
        self._started_at = 0.0
        self._elapsed = 0.0
        self._mic = False                       # Windows starts with the microphone muted
        self._status = ""
        self._last_file = ""
        self._shot_tool = capture.pick(capture.SCREENSHOT_TOOLS)
        self._record_tool = capture.pick(capture.RECORDING_TOOLS)
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)

    # --- what the panel may offer -------------------------------------------------------
    @Property(bool, notify=changed)
    def canScreenshot(self) -> bool:  # noqa: N802
        return self._shot_tool is not None

    @Property(bool, notify=changed)
    def canRecord(self) -> bool:  # noqa: N802
        return self._record_tool is not None

    @Property(bool, notify=changed)
    def recording(self) -> bool:
        return self._recording_process is not None

    @Property(bool, notify=changed)
    def micEnabled(self) -> bool:  # noqa: N802
        return self._mic

    @Property(str, notify=changed)
    def elapsedText(self) -> str:  # noqa: N802
        return capture.elapsed_text(self._elapsed)

    @Property(str, notify=changed)
    def status(self) -> str:
        """One line under the tiles: the last result, or why something is unavailable."""
        if self._status:
            return self._status
        if not self.canScreenshot:
            return capture.missing_reason("screenshot")
        if not self.canRecord:
            return capture.missing_reason("recording")
        return ""

    @Property(str, notify=changed)
    def lastFile(self) -> str:  # noqa: N802
        return self._last_file

    # --- actions ------------------------------------------------------------------------
    @Slot(result=bool)
    def takeScreenshot(self) -> bool:  # noqa: N802
        """Grab the screen. True only when the file really exists afterwards."""
        if self._shot_tool is None:
            self._status = capture.missing_reason("screenshot")
            self.changed.emit()
            return False
        folder = capture.screenshots_dir(self._home)
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / capture.screenshot_name(self._clock())
        command = capture.screenshot_command(target, self._shot_tool)
        try:
            process = self._run(command)
            wait = getattr(process, "wait", None)
            if wait is not None:
                wait(timeout=20)
        except Exception as exc:                       # noqa: BLE001 - shown, never swallowed
            self._status = f"Снимок не сделан: {exc}"
            self.changed.emit()
            return False
        if not target.exists():
            self._status = f"Снимок не сделан: {self._shot_tool.binary} не создал файл"
            self.changed.emit()
            return False
        self._last_file = str(target)
        self._status = f"Снимок сохранён: {target.name}"
        self.changed.emit()
        return True

    @Slot(result=bool)
    def toggleRecording(self) -> bool:  # noqa: N802
        return self.stopRecording() if self.recording else self.startRecording()

    @Slot(result=bool)
    def startRecording(self) -> bool:  # noqa: N802
        if self._record_tool is None:
            self._status = capture.missing_reason("recording")
            self.changed.emit()
            return False
        node = fd = None
        if self._record_tool.name == "ffmpeg":
            try:
                cast = portal.session()
            except portal.PortalError as exc:
                self._status = str(exc)
                self.changed.emit()
                return False
            node, fd = cast.node, cast.fd
        folder = capture.recordings_dir(self._home)
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / capture.recording_name(self._clock())
        command = capture.recording_command(target, node=node, fd=fd,
                                            with_microphone=self._mic, tool=self._record_tool)
        if command is None:
            self._status = capture.missing_reason("recording")
            self.changed.emit()
            return False
        try:
            self._recording_process = self._run(command)
        except Exception as exc:                       # noqa: BLE001 - shown, never swallowed
            self._recording_process = None
            self._status = f"Запись не началась: {exc}"
            self.changed.emit()
            return False
        self._last_file = str(target)
        self._started_at = self._clock()
        self._elapsed = 0.0
        self._status = "Идёт запись"
        self._timer.start()
        self.changed.emit()
        return True

    @Slot(result=bool)
    def stopRecording(self) -> bool:  # noqa: N802
        process = self._recording_process
        if process is None:
            return False
        self._timer.stop()
        for method in ("terminate", "kill"):
            call = getattr(process, method, None)
            if call is None:
                continue
            try:
                call()
                break
            except Exception:                          # noqa: BLE001 - try the harder one
                continue
        wait = getattr(process, "wait", None)
        if wait is not None:
            try:
                wait(timeout=10)
            except Exception:                          # noqa: BLE001 - reported below
                pass
        self._recording_process = None
        name = Path(self._last_file).name if self._last_file else ""
        exists = bool(self._last_file) and Path(self._last_file).exists()
        self._status = (f"Запись сохранена: {name}" if exists
                        else "Запись остановлена, но файл не появился")
        self.changed.emit()
        return True

    @Slot(result=bool)
    def toggleMic(self) -> bool:  # noqa: N802
        """The microphone switch applies to the *next* recording; a live one is not re-encoded."""
        self._mic = not self._mic
        if self.recording:
            self._status = ("Микрофон включится со следующей записи" if self._mic
                            else "Микрофон выключится со следующей записи")
        self.changed.emit()
        return self._mic

    @Slot(result=bool)
    def openCaptures(self) -> bool:  # noqa: N802
        """«Просмотреть мои записи» — open the folder in the file manager."""
        folder = capture.recordings_dir(self._home)
        folder.mkdir(parents=True, exist_ok=True)
        opener = capture.which("xdg-open") or capture.which("dolphin")
        if not opener:
            self._status = "Открыть папку нечем: нет ни xdg-open, ни dolphin"
            self.changed.emit()
            return False
        try:
            self._run([opener, str(folder)])
        except Exception as exc:                       # noqa: BLE001 - shown, never swallowed
            self._status = f"Папка не открылась: {exc}"
            self.changed.emit()
            return False
        return True

    def _tick(self) -> None:
        self._elapsed = self._clock() - self._started_at
        self.changed.emit()


PROC_ROLES = {name: Qt.UserRole + 100 + index for index, name in enumerate(
    ("pid", "ppid", "name", "cmdline", "user", "stateText", "threads", "rss", "cpu",
     "cpuText", "memText", "diskText", "isKernel", "readBytes", "openFiles"))}


class ProcessModel(QAbstractListModel):
    """The Task Manager's list: real processes from /proc, sorted and searched.

    Nothing is sampled unless `active` is true — the window being open is the only thing that
    starts the two-second refresh, and closing it stops every read (ADR-0016). The first sample
    deliberately has no CPU column: one reading of /proc cannot tell you a load, so the cells show
    a dash until the second sample makes a difference available.
    """

    changed = Signal()

    def __init__(self, facet=None, interval_ms: int = 2000) -> None:
        super().__init__()
        self._facet = facet
        self._rows: list[dict] = []
        self._all: list[dict] = []
        self._query = ""
        self._sort_key = "cpu"
        self._descending = True
        self._snapshot = None
        self._summary = None
        self._active = False
        self._cpu_history = taskmanager.History()
        self._memory_history = taskmanager.History()
        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self.refresh)

    @property
    def facet(self):
        if self._facet is None:
            self._facet = system.backend().processes
        return self._facet

    # --- lifecycle: the window decides when the machine is read ---------------------------
    @Slot(bool)
    def setActive(self, active: bool) -> None:  # noqa: N802
        self._active = bool(active)
        if self._active:
            self.refresh()
            self._timer.start()
        else:
            self._timer.stop()

    @Property(bool, notify=changed)
    def active(self) -> bool:
        return self._active

    @Slot()
    def refresh(self) -> None:
        snapshot = self.facet.sample()
        self._snapshot = snapshot
        self._summary = taskmanager.summarise(snapshot)
        self._cpu_history.push(snapshot.cpu)
        self._memory_history.push(snapshot.memory_percent)
        self._all = [process.as_row() for process in snapshot.processes]
        self._apply()

    def _apply(self) -> None:
        rows = [row for row in self._all if taskmanager.matches(row, self._query)]
        rows = taskmanager.sort_rows(rows, self._sort_key, self._descending)
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()
        self.changed.emit()

    # --- view controls --------------------------------------------------------------------
    @Slot(str)
    def search(self, query: str) -> None:
        self._query = query or ""
        self._apply()

    @Slot(str)
    def sortBy(self, key: str) -> None:  # noqa: N802
        """Clicking the active column header reverses it, as in Windows."""
        if key not in taskmanager.COLUMN_KEYS:
            return
        if key == self._sort_key:
            self._descending = not self._descending
        else:
            self._sort_key = key
            self._descending = key in taskmanager.NUMERIC
        self._apply()

    @Property(str, notify=changed)
    def sortKey(self) -> str:  # noqa: N802
        return self._sort_key

    @Property(bool, notify=changed)
    def sortDescending(self) -> bool:  # noqa: N802
        return self._descending

    # --- actions --------------------------------------------------------------------------
    @Slot(int, bool, result="QVariantMap")
    def endTask(self, pid: int, force: bool = False) -> dict:  # noqa: N802
        """«Снять задачу». Returns what the kernel said, never an optimistic success."""
        reading = self.facet.end(int(pid), force=bool(force))
        self.refresh()
        return {"ok": reading.available, "detail": reading.detail, "pid": int(pid)}

    @Slot(int, result="QVariantMap")
    def inspect(self, pid: int) -> dict:
        reading = self.facet.process(int(pid))
        data = {"available": reading.available, "detail": reading.detail,
                "source": reading.source}
        data.update(reading.extra)
        data["memText"] = taskmanager.format_bytes(reading.get("rss"))
        return data

    # --- data -----------------------------------------------------------------------------
    def roleNames(self) -> dict:  # noqa: N802
        return {role: name.encode() for name, role in PROC_ROLES.items()}

    def rowCount(self, parent=QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._rows)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._rows)):
            return None
        row = self._rows[index.row()]
        if role == PROC_ROLES["cpuText"]:
            return taskmanager.format_percent(row.get("cpu"))
        if role == PROC_ROLES["memText"]:
            return taskmanager.format_bytes(row.get("rss"))
        if role == PROC_ROLES["diskText"]:
            return taskmanager.format_bytes(row.get("readBytes"))
        for name, value in PROC_ROLES.items():
            if value == role:
                return row.get(name)
        return None

    @Property(int, notify=changed)
    def count(self) -> int:
        return len(self._rows)

    @Property("QVariantMap", notify=changed)
    def summary(self) -> dict:
        """The header strip. Empty before the first sample — never pre-filled with zeroes."""
        if self._summary is None:
            return {}
        summary = self._summary
        return {"cpu": summary.cpu, "memory": summary.memory, "disk": summary.disk,
                "network": summary.network, "uptime": summary.uptime,
                "processes": summary.processes, "threads": summary.threads,
                "memoryDetail": summary.memory_detail}

    @Property("QVariantList", notify=changed)
    def cores(self) -> list:
        return list(self._snapshot.cores) if self._snapshot else []

    @Property("QVariantList", notify=changed)
    def cpuHistory(self) -> list:  # noqa: N802
        return self._cpu_history.points()

    @Property("QVariantList", notify=changed)
    def memoryHistory(self) -> list:  # noqa: N802
        return self._memory_history.points()

    @Property("QVariantList", notify=changed)
    def gpus(self) -> list:
        """Real cards only. A driver that does not export a load reports the reason instead."""
        from zaldros_backend import processes as backend_processes
        return [{"name": card.detail, "percent": card.percent,
                 "available": card.available, "reason": card.get("reason", "")}
                for card in backend_processes.gpus()]

    @Property("QVariantList", constant=True)
    def columns(self) -> list:
        return [{"key": key, "title": title, "numeric": numeric}
                for key, title, numeric in taskmanager.COLUMNS]


class StartupModel(QAbstractListModel):
    """«Автозагрузка»: freedesktop autostart entries, with a switch that really writes."""

    NAME_R, FILE_R, ENABLED_R, COMMAND_R, WRITABLE_R = (Qt.UserRole + 200 + n for n in range(5))

    changed = Signal()

    def __init__(self, facet=None) -> None:
        super().__init__()
        self._facet = facet
        self._rows: list = []

    @property
    def facet(self):
        if self._facet is None:
            self._facet = system.backend().processes
        return self._facet

    @Slot()
    def refresh(self) -> None:
        self.beginResetModel()
        self._rows = self.facet.startup()
        self.endResetModel()
        self.changed.emit()

    @Slot(int, result="QVariantMap")
    def toggle(self, row: int) -> dict:
        """Flip an entry and read the file back — the switch shows the disk, not the click."""
        if not (0 <= row < len(self._rows)):
            return {"ok": False, "detail": "нет такой строки"}
        entry = self._rows[row]
        result = self.facet.set_startup_enabled(entry.get("file", ""), not entry.get("enabled"))
        self.refresh()
        return {"ok": result.available, "detail": result.detail}

    def roleNames(self) -> dict:  # noqa: N802
        return {self.NAME_R: b"name", self.FILE_R: b"file", self.ENABLED_R: b"enabled",
                self.COMMAND_R: b"command", self.WRITABLE_R: b"writable"}

    def rowCount(self, parent=QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._rows)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._rows)):
            return None
        entry = self._rows[index.row()]
        return {self.NAME_R: entry.detail, self.FILE_R: entry.get("file", ""),
                self.ENABLED_R: bool(entry.get("enabled")),
                self.COMMAND_R: entry.get("command", ""),
                self.WRITABLE_R: bool(entry.get("writable"))}.get(role)

    @Property(int, notify=changed)
    def count(self) -> int:
        return len(self._rows)
