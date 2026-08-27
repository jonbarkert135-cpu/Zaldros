"""Load the Zaldros Sheets QML, optionally backed by a running engine.

    python -m zaldros_sheets render --out sheets.png
    python -m zaldros_sheets render --open book.xlsx --out sheets.png
    python -m zaldros_sheets run

`render` never invents data: with no `--open` and no engine it draws an empty sheet and says so in
the status bar, which is the honest state of an application that has not been given a file.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QFontDatabase, QGuiApplication
from PySide6.QtQuick import QQuickView

from .engine import CalcEngine, EngineError, soffice_path, uno_available
from .model import GridModel, SheetsState, reference

#: QML only borrows the models; Python owns them, and a collected model turns every
#: binding into `null`. Renders in the same process therefore keep them here.
_KEEP: list = []

APP_DIR = Path(__file__).resolve().parents[1]
QML_DIR = APP_DIR / "qml"
ASSETS = APP_DIR.parents[1] / "assets"
FONT_DIR = ASSETS / "fonts"
ICON_DIR = ASSETS / "icons"


def load_font() -> str:
    for ttf in sorted(FONT_DIR.rglob("*.ttf")):
        QFontDatabase.addApplicationFont(str(ttf))
    return "PT Sans" if "PT Sans" in set(QFontDatabase.families()) else "Sans Serif"


class _IconProvider:
    """Serve assets/icons/<group>/<name>.svg to QML as image://zaldrosicon/<group>/<name>."""

    @staticmethod
    def install(engine_or_view) -> None:
        from PySide6.QtCore import QSize
        from PySide6.QtGui import QImage, QPainter
        from PySide6.QtQuick import QQuickImageProvider
        from PySide6.QtSvg import QSvgRenderer

        class Provider(QQuickImageProvider):
            def __init__(self) -> None:
                super().__init__(QQuickImageProvider.ImageType.Image)

            def requestImage(self, path, size, requested):  # noqa: N802 - Qt signature
                width = requested.width() if requested.width() > 0 else 24
                height = requested.height() if requested.height() > 0 else 24
                image = QImage(width, height, QImage.Format.Format_ARGB32)
                image.fill(0)
                svg = ICON_DIR / f"{path}.svg"
                if svg.exists():
                    painter = QPainter(image)
                    QSvgRenderer(str(svg)).render(painter)
                    painter.end()
                if size is not None:
                    size.setWidth(width)
                    size.setHeight(height)
                return image

        engine_or_view.addImageProvider("zaldrosicon", Provider())


def _build(view: QQuickView, *, workbook, engine_state: str, light: bool, document: str):
    ref = reference()
    family = load_font()
    grid = GridModel(rows=40, columns=16, workbook=workbook)
    state = SheetsState(grid, engine_state=engine_state, light=light, document=document)
    palette = ref["palette"]["light" if light else "dark"]
    theme = {"family": family, "text": palette["text"], "gridline": palette["gridline"],
             "accent": palette["accent"]}
    context = view.rootContext()
    context.setContextProperty("ref", ref)
    context.setContextProperty("gridModel", grid)
    context.setContextProperty("book", state)
    context.setContextProperty("theme", theme)
    context.setContextProperty("uiFontFamily", family)
    return grid, state


def _open(path: str | None):
    """Start the engine and open a file, or explain in one line why we could not."""
    if path is None:
        return None, None, "No workbook open."
    if soffice_path() is None or not uno_available():
        return None, None, "Engine unavailable: LibreOffice or the UNO bridge is missing."
    try:
        engine = CalcEngine().start()
        book = engine.open(path)
    except EngineError as exc:
        return None, None, f"Engine error: {exc}"
    return engine, book, f"{Path(path).name} — engine: LibreOffice Calc"


def render(out: str, *, open_path: str | None = None, light: bool = True,
           width: int = 1280, height: int = 800, document: str = "Book1") -> str:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])
    engine, workbook, status = _open(open_path)
    view = QQuickView()
    _IconProvider.install(view.engine())
    _KEEP.append(_build(view, workbook=workbook, engine_state=status, light=light,
                        document=Path(open_path).stem if open_path else document))
    view.setSource(QUrl.fromLocalFile(str(QML_DIR / "Sheets.qml")))
    if view.status() == QQuickView.Status.Error:
        for error in view.errors():
            print(error.toString(), file=sys.stderr)
        raise SystemExit("the Sheets QML did not load")
    view.resize(width, height)
    view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
    view.show()
    app.processEvents()
    image = view.grabWindow()
    target = Path(out).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(str(target))
    if workbook is not None:
        workbook.close()
    if engine is not None:
        engine.stop()
    return str(target)


def run(open_path: str | None = None) -> int:
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    engine, workbook, status = _open(open_path)
    view = QQuickView()
    _IconProvider.install(view.engine())
    _KEEP.append(_build(view, workbook=workbook, engine_state=status, light=True,
                        document=Path(open_path).stem if open_path else "Book1"))
    view.setSource(QUrl.fromLocalFile(str(QML_DIR / "Sheets.qml")))
    view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
    view.resize(1280, 800)
    view.show()
    code = app.exec()
    if workbook is not None:
        workbook.close()
    if engine is not None:
        engine.stop()
    return code
