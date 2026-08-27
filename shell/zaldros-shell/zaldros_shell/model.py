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

from .backend import AppEntry, format_clock, load_pinned, memory_percent, read_running_commands
from .desktop_entries import DesktopApp, discover, launch
from . import clipboard as clipboard_history
from . import capture, portal
from . import files, hostinfo, prefs, settingspages, system, weather

NAME, EXEC, ICON, COLOR, RUNNING, INSTALLED, SUBTITLE = (Qt.UserRole + n for n in range(7))


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

    def __init__(self, home: str | None = None, limit: int = 6) -> None:
        super().__init__()
        self._entries = files.recent_files(home, limit)

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


class SettingsTree(QObject):
    """The Settings information architecture (settingspages.py) as plain data for QML."""

    changed = Signal()

    def __init__(self, pages: dict | None = None) -> None:
        super().__init__()
        self._pages = pages if pages is not None else settingspages.to_variant(settingspages.build())

    @Slot()
    def refresh(self) -> None:
        self._pages = settingspages.to_variant(settingspages.build())
        self.changed.emit()

    @Slot(str, result="QVariantMap")
    def page(self, page_id: str) -> dict:
        return self._pages.get(page_id, {"id": page_id, "title": "", "parent": "", "entries": []})

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
        """Take whatever is on the clipboard now. Returns True when the history changed."""
        if self._clip is None:
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
