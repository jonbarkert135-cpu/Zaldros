"""Load the Zaldros Shell QML with its backend models.

Two entry points:
  `run()`        — show the shell (needs a real display or QT_QPA_PLATFORM=offscreen)
  `render(...)`  — render the shell to a PNG, used for visual evidence and regression tests
                   (spec PART 5 §8: visual regression on real renders, not on hand-drawn mockups).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import json

from PySide6.QtCore import (QCoreApplication, QMetaObject, QObject, QPointF, QTimer, QUrl,
                            Q_ARG)
from PySide6.QtGui import QFont, QFontDatabase, QGuiApplication
from PySide6.QtQuick import QQuickView

from .icons import IconProvider
from .model import (AppModel, ClipboardModel, FileModel, GameBarModel, HostInfo, InstalledAppModel,
                    DeviceModel, Prefs, ProcessModel, TerminalModel, RecentModel, SettingsControls, SettingsTree, StartupModel,
                    WeatherState, ShellState, SystemState)

QML_DIR = Path(__file__).resolve().parent.parent / "qml"
def _assets_dir() -> Path:
    """Find the asset tree. In the repo it sits three levels up; inside the ISO the shell is
    installed flat at /opt/zaldros, where that walk lands on "/assets" and every font, icon and
    wallpaper silently disappears — which is half of the services/legacy black screen."""
    candidates = [Path(os.environ["ZALDROS_ASSETS"])] if os.environ.get("ZALDROS_ASSETS") else []
    here = Path(__file__).resolve()
    candidates += [here.parents[3] / "assets", here.parents[1] / "assets", Path("/opt/zaldros/assets")]
    for path in candidates:
        if (path / "wallpaper").is_dir():
            return path
    return candidates[-1]  # nothing found: keep a stable path, missing files stay visible as errors


ASSETS = _assets_dir()
FONT_DIR = ASSETS / "fonts"

# Ordered preference for the UI family. The first entry that both loaded *and* covers Cyrillic
# wins. Selawik was metrically Segoe UI but its cmap is Latin-only (383 glyphs, zero Cyrillic), so
# the Russian interface fell through to whatever fontconfig offered — DejaVu Sans on our ISO,
# which is why every label looked wrong. PT Sans replaced it: measured against the Windows 11
# capture in assets/refs it is the closest Cyrillic match we can ship (tools/visual/font_match.py).
# Coverage is now a condition, not an assumption.
UI_FONT_PREFERENCE = ("PT Sans",)
UI_FONT_ENV = "ZALDROS_UI_FONT"          # override, used by the font comparison tool


def _covers_cyrillic(family: str) -> bool:
    return QFontDatabase.WritingSystem.Cyrillic in QFontDatabase.writingSystems(family)


def load_fonts() -> str:
    """Register the vendored faces and return the family actually usable for the UI.

    Never returns a family that cannot draw the interface's own alphabet: a font that renders
    boxes or silently falls back is worse than admitting we are on the host default.
    """
    for ttf in sorted(FONT_DIR.rglob("*.ttf")):
        QFontDatabase.addApplicationFont(str(ttf))
    available = set(QFontDatabase.families())
    override = os.environ.get(UI_FONT_ENV)
    wanted = [override] if override else list(UI_FONT_PREFERENCE)
    for family in wanted:
        if family in available and _covers_cyrillic(family):
            return family
    fallback = QFont().defaultFamily()
    print(f"ui font: none of {wanted} is installed with Cyrillic coverage, using {fallback}",
          flush=True)
    return fallback


def build_view(locale: str = "ru", tick: bool = True) -> tuple[QQuickView, list]:
    family = load_fonts()
    QGuiApplication.setFont(QFont(family, 9))
    view = QQuickView()
    view.engine().addImportPath(str(QML_DIR.parent))
    view.engine().addImportPath(str(QML_DIR))
    installed = InstalledAppModel()
    model = AppModel(installed=None)
    state = ShellState(locale=locale, tick=tick)
    system_state = SystemState()
    file_model = FileModel()
    recent_model = RecentModel()
    host_info = HostInfo()
    weather_state = WeatherState(fetch=tick)
    settings_controls = SettingsControls()
    settings_tree = SettingsTree(controls=settings_controls)
    user_prefs = Prefs()
    clipboard_model = ClipboardModel()
    game_bar_model = GameBarModel()
    # The Task Manager is constructed but idle: ProcessModel reads /proc only after the window
    # sets it active, so a session that never opens it costs nothing (ADR-0016).
    process_model = ProcessModel()
    startup_model = StartupModel()
    device_model = DeviceModel()
    terminal_model = TerminalModel()
    context = view.engine().rootContext()
    context.setContextProperty("appModel", model)
    context.setContextProperty("installedModel", installed)
    context.setContextProperty("shellState", state)
    context.setContextProperty("systemState", system_state)
    context.setContextProperty("fileModel", file_model)
    context.setContextProperty("recentModel", recent_model)
    context.setContextProperty("hostInfo", host_info)
    context.setContextProperty("weatherState", weather_state)
    context.setContextProperty("settingsTree", settings_tree)
    context.setContextProperty("settingsControls", settings_controls)
    context.setContextProperty("prefs", user_prefs)
    context.setContextProperty("clipboardModel", clipboard_model)
    context.setContextProperty("gameBarModel", game_bar_model)
    context.setContextProperty("processModel", process_model)
    context.setContextProperty("startupModel", startup_model)
    context.setContextProperty("deviceModel", device_model)
    context.setContextProperty("terminalModel", terminal_model)
    context.setContextProperty("uiFontFamily", family)
    view.engine().addImageProvider("zaldrosicon", IconProvider(ASSETS / "icons" / "fluent"))
    context.setContextProperty(
        "wallpaperUrl", QUrl.fromLocalFile(str(ASSETS / "wallpaper" / "zaldros-default.png")).toString())
    view.setSource(QUrl.fromLocalFile(str(QML_DIR / "Shell.qml")))
    if view.status() != QQuickView.Ready:
        errors = "\n".join(str(error.toString()) for error in view.errors())
        raise RuntimeError(f"QML failed to load:\n{errors}")
    return view, [model, installed, state, system_state, file_model, recent_model, host_info,
                  weather_state, settings_tree, settings_controls, user_prefs, clipboard_model,
                  game_bar_model, process_model, startup_model, device_model, terminal_model]


_KEEPALIVE: list = []  # QML context properties must outlive the call; Python must hold a reference


def render(output: str, start_open: bool = False, width: int = 1600, height: int = 1000,
           locale: str = "ru", quick_open: bool = False, context_open: bool = False,
           light: bool = False, search_open: bool = False, notifications_open: bool = False,
           clipboard_open: bool = False, game_bar_open: bool = False,
           focused_window: str = "explorer", settings_page: int = 1,
           task_manager_open: bool = False, task_manager_page: int = 0,
           device_manager_open: bool = False, terminal_open: bool = False,
           geometry_output: str | None = None) -> str:
    """Render one frame to `output`. Returns the path. Raises if QML did not load."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QCoreApplication.instance() or QGuiApplication(sys.argv[:1])
    view, backends = build_view(locale=locale, tick=False)
    _KEEPALIVE.extend([view, *backends])
    view.setWidth(width)
    view.setHeight(height)
    # The live session resizes the root item to the screen (see run(), SizeRootObjectToView).
    # Renders used to leave it on the 1600x1000 design canvas, so a window could hang off the edge
    # of a real 1280x800 screen — run #29 — and no offscreen render would ever show it.
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    root = view.rootObject()
    root.setProperty("width", width)
    root.setProperty("height", height)
    root.setProperty("lightMode", light)
    root.setProperty("startOpen", start_open)
    root.setProperty("quickOpen", quick_open)
    root.setProperty("searchOpen", search_open)
    root.setProperty("notificationsOpen", notifications_open)
    root.setProperty("clipboardOpen", clipboard_open)
    root.setProperty("gameBarOpen", game_bar_open)
    root.setProperty("contextOpen", context_open)
    root.setProperty("focusedWindow", focused_window)
    root.setProperty("settingsPage", settings_page)
    if terminal_open:
        QMetaObject.invokeMethod(root, "toggleWindow", Q_ARG("QVariant", "terminal"))
        root.setProperty("focusedWindow", "terminal")
    if device_manager_open:
        QMetaObject.invokeMethod(root, "toggleWindow", Q_ARG("QVariant", "devicemanager"))
        root.setProperty("focusedWindow", "devicemanager")
    if task_manager_open:
        # Opening it here rather than by default keeps every other frame byte-identical.
        QMetaObject.invokeMethod(root, "toggleWindow", Q_ARG("QVariant", "taskmanager"))
        root.setProperty("focusedWindow", "taskmanager")
        window = root.findChild(QObject, "taskManagerWindow")
        if window is not None:
            page = window.findChild(QObject, "taskManagerRail")
            if page is not None and page.parent() is not None:
                page.parent().setProperty("page", task_manager_page)
    view.show()
    result: dict[str, bool] = {}

    def grab() -> None:
        if geometry_output:
            write_hit_boxes(view, geometry_output)
        image = view.grabWindow()
        result["ok"] = image.save(output)
        result["size"] = (image.width(), image.height())
        app.quit()

    QTimer.singleShot(700, grab)
    app.exec()
    view.hide()
    # Unload the QML tree before the backend objects go out of scope, otherwise bindings evaluate
    # against destroyed context properties and Qt logs spurious TypeErrors during teardown.
    view.setSource(QUrl())
    if not result.get("ok"):
        raise RuntimeError(f"failed to write {output}")
    return output


# Every named item the UI test clicks or the visual parity tool measures. Names live on the QML
# items themselves (objectName), so a renamed component fails loudly here instead of silently.
NAMED_ITEMS = ("taskbar", "taskbarGroup", "startButton", "taskbarSearch", "taskViewButton",
               "widgetsButton", "weatherIcon", "weatherTemperature", "weatherCondition",
               "trayGroup", "trayQuickButton", "clock", "notificationButton",
               "startPanel", "startSearch", "startPinnedGrid", "startFooter",
               "searchFlyout", "notificationCentre", "quickPanel", "clipboardFlyout", "gameBarFlyout", "gameBarToolbar", "contextMenu",
               "explorerWindow", "explorerTabStrip", "explorerNavBar", "explorerCommandBar",
               "explorerSidebar", "explorerFileList", "settingsWindow", "settingsRail",
               "settingsBody", "titleBar", "captionButtons")


def hit_boxes(view: QQuickView) -> dict:
    """Screen coordinates of the widgets an external UI test needs to click.

    The taskbar group is centred and its width depends on how many applications are pinned, so a
    host-side test cannot compute the Start button position: it has to be told. Run #25 clicked a
    guessed point on an empty part of the bar and reported FAIL for a shell that was fine.
    """
    boxes: dict = {}
    root = view.rootObject()
    if root is None:
        return boxes
    for name in NAMED_ITEMS:
        item = root.findChild(QObject, name)
        if item is None:
            continue
        width = float(item.property("width") or 0)
        height = float(item.property("height") or 0)
        centre = item.mapToItem(root, QPointF(width / 2, height / 2))
        origin = item.mapToItem(root, QPointF(0, 0))
        boxes[name] = {"x": round(centre.x()), "y": round(centre.y()),
                       "left": round(origin.x()), "top": round(origin.y()),
                       "width": round(width), "height": round(height)}
    return boxes


def write_hit_boxes(view: QQuickView, path: str = "/tmp/zaldros-ui-geometry.json") -> None:
    """Publish the hit boxes for the in-guest UI test. Failure here must never kill the shell."""
    try:
        payload = {"screen": {"width": view.width(), "height": view.height()},
                   "items": hit_boxes(view)}
        Path(path).write_text(json.dumps(payload, ensure_ascii=False))
    except Exception as exc:                                    # noqa: BLE001 - diagnostics only
        print(f"hit-box export failed: {exc}", flush=True)


def run() -> int:
    app = QGuiApplication(sys.argv)
    view, backends = build_view()
    _KEEPALIVE.extend([view, *backends])
    # The shell is the desktop: fill the output instead of opening a 1600x1000 window on a
    # smaller screen (KWin then shows bare compositor background around/behind it).
    screen = app.primaryScreen()
    if screen is not None:
        size = screen.geometry().size()
        view.resize(size)
        view.rootObject().setProperty("width", size.width())
        view.rootObject().setProperty("height", size.height())
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    view.showFullScreen()
    # Once the first frame is laid out the taskbar geometry is final; publish it for the UI test.
    QTimer.singleShot(2000, lambda: write_hit_boxes(view))
    return app.exec()
