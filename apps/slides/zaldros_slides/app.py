# SPDX-License-Identifier: GPL-3.0-or-later
"""Load the Zaldros Slides QML, optionally backed by a running engine.

    python -m zaldros_slides render --out slides.png
    python -m zaldros_slides render --open deck.pptx --out slides.png
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QFontDatabase, QGuiApplication
from PySide6.QtQuick import QQuickView

from .engine import EngineError, ImpressEngine, impress_available, soffice_path, uno_available
from .model import DeckModel

_KEEP: list = []
APP_DIR = Path(__file__).resolve().parents[1]
QML_DIR = APP_DIR / "qml"
FONT_DIR = APP_DIR.parents[1] / "assets" / "fonts"


def load_font() -> str:
    for ttf in sorted(FONT_DIR.rglob("*.ttf")):
        QFontDatabase.addApplicationFont(str(ttf))
    return "PT Sans" if "PT Sans" in set(QFontDatabase.families()) else "Sans Serif"


def _open(path: str | None):
    if soffice_path() is None or not uno_available() or not impress_available():
        return None, None
    try:
        engine = ImpressEngine().start()
        deck = engine.open(path) if path else engine.new_presentation()
    except EngineError:
        return None, None
    return engine, deck


def render(out: str, *, open_path: str | None = None, width: int = 1280,
           height: int = 800) -> str:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])
    engine, deck = _open(open_path)
    view = QQuickView()
    model = DeckModel(deck)
    _KEEP.append(model)
    context = view.rootContext()
    context.setContextProperty("deck", model)
    context.setContextProperty("uiFontFamily", load_font())
    view.setSource(QUrl.fromLocalFile(str(QML_DIR / "Slides.qml")))
    if view.status() == QQuickView.Status.Error:
        for error in view.errors():
            print(error.toString(), file=sys.stderr)
        raise SystemExit("the Slides QML did not load")
    view.resize(width, height)
    view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
    view.show()
    app.processEvents()
    image = view.grabWindow()
    target = Path(out).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(str(target))
    if deck is not None:
        deck.close()
    if engine is not None:
        engine.stop()
    return str(target)
