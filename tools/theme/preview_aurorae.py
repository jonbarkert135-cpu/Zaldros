#!/usr/bin/env python3
"""Render what KWin will draw from our Aurorae theme — before spending an ISO build on it.

Boot run 33113315031 shipped a decoration whose caption buttons came out as huge white blocks:
Aurorae scales every element to the *bounding box* of its SVG id, and our glyph-only groups had a
10 px box that got stretched over the whole 46 x 32 button. That class of mistake is invisible in
the SVG source and obvious in a picture, so this script composes the theme the way Aurorae does —
fixed corners, stretched middles, buttons painted into their slots — and writes a PNG.

Run: QT_QPA_PLATFORM=offscreen python3 tools/theme/preview_aurorae.py \
        --variant Zaldros-Dark --width 640 --height 220 --out /tmp/deco.png
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

REPO = Path(__file__).resolve().parents[2]
AURORAE = REPO / "assets" / "themes" / "aurorae"
REFERENCE = REPO / "system" / "theme" / "win11-reference.json"


def _paint(renderer: QSvgRenderer, painter: QPainter, element: str, rect: QRectF) -> None:
    renderer.render(painter, element, rect)


def render(variant: str, width: int, height: int, state: str = "active") -> QImage:
    window = json.loads(REFERENCE.read_text(encoding="utf-8"))["window"]
    title = window["title_bar_height"]
    bw = window["caption_button_width"]
    bh = window["caption_button_height"]
    corner = max(window["corner_radius"] + 4, 12)

    deco = QSvgRenderer(str(AURORAE / variant / "decoration.svg"))
    prefix = "decoration-" if state == "active" else "decoration-inactive-"

    image = QImage(width, height, QImage.Format_ARGB32)
    image.fill(QColor("#0b3b6f"))                       # a desktop behind it, to see the corners
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing, True)

    mid_w = width - 2 * corner
    mid_h = height - title - corner
    _paint(deco, painter, prefix + "topleft", QRectF(0, 0, corner, title))
    _paint(deco, painter, prefix + "top", QRectF(corner, 0, mid_w, title))
    _paint(deco, painter, prefix + "topright", QRectF(width - corner, 0, corner, title))
    _paint(deco, painter, prefix + "left", QRectF(0, title, corner, mid_h))
    _paint(deco, painter, prefix + "center", QRectF(corner, title, mid_w, mid_h))
    _paint(deco, painter, prefix + "right", QRectF(width - corner, title, corner, mid_h))
    _paint(deco, painter, prefix + "bottomleft", QRectF(0, height - corner, corner, corner))
    _paint(deco, painter, prefix + "bottom", QRectF(corner, height - corner, mid_w, corner))
    _paint(deco, painter, prefix + "bottomright",
           QRectF(width - corner, height - corner, corner, corner))

    # RightButtons=IAX -> minimize, maximize, close, flush to the right edge, no spacing
    order = [("minimize", "active"), ("maximize", "hover"), ("close", "hover")]
    x = width - bw * len(order)
    for kind, button_state in order:
        svg = QSvgRenderer(str(AURORAE / variant / f"{kind}.svg"))
        _paint(svg, painter, f"{button_state}-center", QRectF(x, 0, bw, bh))
        x += bw

    painter.setPen(QColor(225, 225, 225) if variant.endswith("Dark") else QColor(26, 26, 26))
    font = painter.font()
    font.setPixelSize(window["title_font"])
    painter.setFont(font)
    painter.drawText(QRectF(window["title_left_margin"], 0, width, title),
                     int(Qt.AlignVCenter | Qt.AlignLeft), "Home — Dolphin")
    painter.end()
    return image


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", default="Zaldros-Dark")
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=220)
    parser.add_argument("--state", default="active", choices=("active", "inactive"))
    parser.add_argument("--out", default="/tmp/aurorae-preview.png")
    args = parser.parse_args()
    app = QGuiApplication.instance() or QGuiApplication([])  # QImage text needs a font database
    _ = app
    image = render(args.variant, args.width, args.height, args.state)
    image.save(args.out)
    print(f"{args.variant} {args.state}: {args.width}x{args.height} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
