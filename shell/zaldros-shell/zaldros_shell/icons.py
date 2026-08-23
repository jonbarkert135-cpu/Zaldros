"""Recoloured Fluent icons for QML.

Fluent UI System Icons (Microsoft, MIT) ship with a fixed `fill="#212121"`. QML needs them in the
current theme colour, and MultiEffect shaders are unavailable under the software rasteriser used for
headless renders — so the SVG source is recoloured by string substitution and rasterised here.

QML side: `source: "image://zaldrosicon/wifi?%23ffffff"` (Theme.iconUrl() builds it).
"""
from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QImage, QPainter
from PySide6.QtQuick import QQuickImageProvider
from PySide6.QtSvg import QSvgRenderer

FLUENT_BLACK = "#212121"


class IconProvider(QQuickImageProvider):
    """Serves `image://zaldrosicon/<name>?<#rrggbb>`. Unknown names return a null image, which QML
    reports as Image.Error — a missing icon must be visible as missing, not silently blank."""

    def __init__(self, directory: Path) -> None:
        super().__init__(QQuickImageProvider.Image)
        self.directory = Path(directory)

    def requestImage(self, request_id: str, size: QSize, requested: QSize) -> QImage:
        name, _, colour = unquote(request_id).partition("?")   # QML sends "%23rrggbb"
        if name.startswith("app/"):
            return self._app_icon(name[4:], max(requested.width(), 32))
        path = self.directory / f"{name}.svg"
        if not path.is_file():
            return QImage()
        source = path.read_text(encoding="utf-8")
        if colour:
            source = source.replace(FLUENT_BLACK, colour)
        renderer = QSvgRenderer(source.encode("utf-8"))
        side = max(requested.width(), requested.height(), 16)
        image = QImage(side, side, QImage.Format_ARGB32_Premultiplied)
        image.fill(Qt.transparent)
        painter = QPainter(image)
        renderer.render(painter)
        painter.end()
        return image   # the engine reads the real size off the returned image

    def _app_icon(self, name: str, side: int) -> QImage:
        """Real application icon from the host's icon theme. Returns a null image when the theme has
        no such icon, and QML then falls back to the lettered tile — an app never gets a wrong icon.
        """
        icon = QIcon.fromTheme(name)
        return QImage() if icon.isNull() else icon.pixmap(side, side).toImage()
