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

from PySide6.QtCore import QCoreApplication, QTimer, QUrl
from PySide6.QtGui import QFont, QFontDatabase, QGuiApplication
from PySide6.QtQuick import QQuickView

from .icons import IconProvider
from .model import AppModel, InstalledAppModel, ShellState, SystemState

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
FONT_DIR = ASSETS / "fonts" / "selawik"


def load_fonts() -> str:
    """Register the vendored Selawik faces (Microsoft, SIL OFL 1.1). Returns the family actually
    available, so the caller never claims a font that failed to load."""
    for ttf in sorted(FONT_DIR.glob("*.ttf")):
        QFontDatabase.addApplicationFont(str(ttf))
    return "Selawik" if "Selawik" in QFontDatabase.families() else QFont().defaultFamily()


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
    context = view.engine().rootContext()
    context.setContextProperty("appModel", model)
    context.setContextProperty("installedModel", installed)
    context.setContextProperty("shellState", state)
    context.setContextProperty("systemState", system_state)
    context.setContextProperty("uiFontFamily", family)
    view.engine().addImageProvider("zaldrosicon", IconProvider(ASSETS / "icons" / "fluent"))
    context.setContextProperty(
        "wallpaperUrl", QUrl.fromLocalFile(str(ASSETS / "wallpaper" / "zaldros-default.png")).toString())
    view.setSource(QUrl.fromLocalFile(str(QML_DIR / "Shell.qml")))
    if view.status() != QQuickView.Ready:
        errors = "\n".join(str(error.toString()) for error in view.errors())
        raise RuntimeError(f"QML failed to load:\n{errors}")
    return view, [model, installed, state, system_state]


_KEEPALIVE: list = []  # QML context properties must outlive the call; Python must hold a reference


def render(output: str, start_open: bool = False, width: int = 1600, height: int = 1000,
           locale: str = "ru", quick_open: bool = False, context_open: bool = False,
           light: bool = False) -> str:
    """Render one frame to `output`. Returns the path. Raises if QML did not load."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QCoreApplication.instance() or QGuiApplication(sys.argv[:1])
    view, backends = build_view(locale=locale, tick=False)
    _KEEPALIVE.extend([view, *backends])
    view.setWidth(width)
    view.setHeight(height)
    root = view.rootObject()
    root.setProperty("lightMode", light)
    root.setProperty("startOpen", start_open)
    root.setProperty("quickOpen", quick_open)
    root.setProperty("contextOpen", context_open)
    view.show()
    result: dict[str, bool] = {}

    def grab() -> None:
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
    return app.exec()
