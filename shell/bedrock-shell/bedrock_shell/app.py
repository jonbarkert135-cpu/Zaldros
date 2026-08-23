"""Load the Bedrock Shell QML with its backend models.

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
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickView

from .model import AppModel, ShellState

QML_DIR = Path(__file__).resolve().parent.parent / "qml"


def build_view(locale: str = "ru", tick: bool = True) -> tuple[QQuickView, AppModel, ShellState]:
    view = QQuickView()
    view.engine().addImportPath(str(QML_DIR.parent))
    view.engine().addImportPath(str(QML_DIR))
    model = AppModel()
    state = ShellState(locale=locale, tick=tick)
    context = view.engine().rootContext()
    context.setContextProperty("appModel", model)
    context.setContextProperty("shellState", state)
    view.setSource(QUrl.fromLocalFile(str(QML_DIR / "Shell.qml")))
    if view.status() != QQuickView.Ready:
        errors = "\n".join(str(error.toString()) for error in view.errors())
        raise RuntimeError(f"QML failed to load:\n{errors}")
    return view, model, state


_KEEPALIVE: list = []  # QML context properties must outlive the call; Python must hold a reference


def render(output: str, start_open: bool = False, width: int = 1280, height: int = 800,
           locale: str = "ru") -> str:
    """Render one frame to `output`. Returns the path. Raises if QML did not load."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QCoreApplication.instance() or QGuiApplication(sys.argv[:1])
    view, model, state = build_view(locale=locale, tick=False)
    _KEEPALIVE.extend([view, model, state])
    view.setWidth(width)
    view.setHeight(height)
    view.rootObject().setProperty("startOpen", start_open)
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
    view, model, state = build_view()
    view.resize(1280, 800)
    view.show()
    return app.exec()
