# SPDX-License-Identifier: GPL-3.0-or-later
"""Load the Zaldros Writer QML, optionally backed by a running engine.

    python -m zaldros_writer render --out writer.png
    python -m zaldros_writer render --open letter.docx --out writer.png
    python -m zaldros_writer run

`render` never invents text: with no engine it draws an empty page and the status bar says which
package is missing. That is the honest state of a word processor with no engine behind it.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QFontDatabase, QGuiApplication
from PySide6.QtQuick import QQuickView

from .engine import EngineError, WriterEngine, soffice_path, uno_available, writer_available
from .model import DocumentModel, reference

_KEEP: list = []

APP_DIR = Path(__file__).resolve().parents[1]
QML_DIR = APP_DIR / "qml"
FONT_DIR = APP_DIR.parents[1] / "assets" / "fonts"


def load_font() -> str:
    for ttf in sorted(FONT_DIR.rglob("*.ttf")):
        QFontDatabase.addApplicationFont(str(ttf))
    return "PT Sans" if "PT Sans" in set(QFontDatabase.families()) else "Sans Serif"


def _open(path: str | None):
    """Start the engine and open a file, or say in one line why we could not."""
    if soffice_path() is None:
        return None, None
    if not uno_available() or not writer_available():
        return None, None
    try:
        engine = WriterEngine().start()
        document = engine.open(path) if path else engine.new_document()
    except EngineError:
        return None, None
    return engine, document


def _build(view: QQuickView, document) -> DocumentModel:
    family = load_font()
    model = DocumentModel(document)
    context = view.rootContext()
    context.setContextProperty("ref", reference())
    context.setContextProperty("document", model)
    context.setContextProperty("uiFontFamily", family)
    return model


def render(out: str, *, open_path: str | None = None, width: int = 1280,
           height: int = 800) -> str:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])
    engine, document = _open(open_path)
    view = QQuickView()
    _KEEP.append(_build(view, document))
    view.setSource(QUrl.fromLocalFile(str(QML_DIR / "Writer.qml")))
    if view.status() == QQuickView.Status.Error:
        for error in view.errors():
            print(error.toString(), file=sys.stderr)
        raise SystemExit("the Writer QML did not load")
    view.resize(width, height)
    view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
    view.show()
    app.processEvents()
    image = view.grabWindow()
    target = Path(out).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(str(target))
    if document is not None:
        document.close()
    if engine is not None:
        engine.stop()
    return str(target)


def run(open_path: str | None = None) -> int:
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    engine, document = _open(open_path)
    view = QQuickView()
    _KEEP.append(_build(view, document))
    view.setSource(QUrl.fromLocalFile(str(QML_DIR / "Writer.qml")))
    view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
    view.resize(1280, 800)
    view.show()
    code = app.exec()
    if document is not None:
        document.close()
    if engine is not None:
        engine.stop()
    return code
