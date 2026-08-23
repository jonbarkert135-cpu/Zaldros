"""Generate the Zaldros default wallpaper — our own artwork, not a Microsoft asset.

    QT_QPA_PLATFORM=offscreen python generate.py [--width 3840] [--height 2160]

Draws layered translucent ribbons over a deep blue radial field: the visual language of a modern
desktop wallpaper without copying anyone's image.
"""
from __future__ import annotations

import argparse
import math
import sys

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import (QColor, QGuiApplication, QImage, QLinearGradient, QPainter, QPainterPath,
                           QPen, QRadialGradient)

DARK = QColor("#04101f")
DEEP = QColor("#0a2547")
GLOW = QColor("#1b6fb8")


def ribbon(painter: QPainter, w: int, h: int, phase: float, spread: float, colour: QColor) -> None:
    """One silky band: a sweep of thin bezier strokes fanned out along a common curve."""
    for i in range(90):
        t = i / 89
        offset = (t - 0.5) * spread * h
        path = QPainterPath(QPointF(-0.15 * w, h * 0.55 + offset + math.sin(phase) * 0.1 * h))
        path.cubicTo(QPointF(w * 0.25, h * (0.20 + 0.35 * math.sin(phase + t)) + offset),
                     QPointF(w * 0.70, h * (0.85 - 0.40 * math.cos(phase * 1.3 + t)) + offset),
                     QPointF(w * 1.15, h * 0.35 + offset * 0.6))
        alpha = int(46 * math.sin(math.pi * t) ** 2)
        pen = QPen(QColor(colour.red(), colour.green(), colour.blue(), alpha))
        pen.setWidthF(max(1.0, h / 260))
        painter.setPen(pen)
        painter.drawPath(path)


def render(width: int, height: int, output: str) -> str:
    image = QImage(width, height, QImage.Format_RGB32)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)

    base = QLinearGradient(0, 0, width, height)
    base.setColorAt(0.0, DARK)
    base.setColorAt(0.55, DEEP)
    base.setColorAt(1.0, DARK)
    painter.fillRect(image.rect(), base)

    halo = QRadialGradient(width * 0.42, height * 0.52, max(width, height) * 0.55)
    halo.setColorAt(0.0, QColor(GLOW.red(), GLOW.green(), GLOW.blue(), 150))
    halo.setColorAt(1.0, QColor(GLOW.red(), GLOW.green(), GLOW.blue(), 0))
    painter.fillRect(image.rect(), halo)

    painter.setCompositionMode(QPainter.CompositionMode_Plus)
    for phase, spread, colour in ((0.4, 0.22, QColor("#7fd0ff")), (1.7, 0.30, QColor("#3d8fdd")),
                                  (2.9, 0.18, QColor("#b9e6ff")), (4.1, 0.26, QColor("#215ea8"))):
        ribbon(painter, width, height, phase, spread, colour)

    painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
    vignette = QRadialGradient(width / 2, height / 2, max(width, height) * 0.72)
    vignette.setColorAt(0.55, QColor(0, 0, 0, 0))
    vignette.setColorAt(1.0, QColor(0, 0, 0, 170))
    painter.fillRect(image.rect(), vignette)
    painter.end()

    if not image.save(output):
        raise RuntimeError(f"could not write {output}")
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--width", type=int, default=3840)
    parser.add_argument("--height", type=int, default=2160)
    parser.add_argument("--out", default="zaldros-default.png")
    args = parser.parse_args()
    QGuiApplication(sys.argv[:1])
    print(render(args.width, args.height, args.out))


if __name__ == "__main__":
    main()
