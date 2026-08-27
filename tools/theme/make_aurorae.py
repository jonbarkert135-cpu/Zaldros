#!/usr/bin/env python3
"""Generate the Zaldros Aurorae window decoration — ours, from our own numbers.

Until now the title bars of real applications (Dolphin, Konsole) were drawn by a borrowed GPL-3
theme from the KDE store. ADR-0010 says the cursor pack is the only thing we borrow, so this
script draws the decoration instead: nine SVG slices, five button states each, in both a dark and
a light variant, all generated from `system/theme/win11-reference.json → window` so the title bar
is 32 px, the caption buttons are 46 × 32 and the corners are 8 px because those are the measured
Windows 11 numbers, not because they looked about right.

Aurorae is KWin's SVG decoration engine (`kwin-style-aurorae`) and needs no Plasma shell, which is
why a Zaldros session can use it at all. It renders elements out of `decoration.svg` by id:

    decoration-{topleft,top,topright,left,center,right,bottomleft,bottom,bottomright}
    decoration-inactive-…  — the same nine for an unfocused window
    shadow_active / shadow_inactive, plus the hint-*-margin rectangles

and each button file by state id: active-center / hover-center / pressed-center /
deactivated-center / inactive-center.

Run: python3 tools/theme/make_aurorae.py [--out assets/themes/aurorae]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
REFERENCE = REPO / "system" / "theme" / "win11-reference.json"

# Our palette. Windows-neutral greys, the same ones the shell uses (qml/ZaldrosTheme/Theme.qml).
PALETTES = {
    "Zaldros-Dark": {
        "title": "#202020",
        "title_inactive": "#1c1c1c",
        "body": "#202020",
        "border": "#3a3a3a",
        "border_inactive": "#2c2c2c",
        "glyph": "#ffffff",
        "glyph_inactive": "#9a9a9a",
        "hover": "#ffffff",
        "hover_opacity": 0.08,
        "pressed_opacity": 0.05,
        "text": "225,225,225",
        "text_inactive": "150,150,150",
    },
    "Zaldros": {
        "title": "#f3f3f3",
        "title_inactive": "#fafafa",
        "body": "#f3f3f3",
        "border": "#d8d8d8",
        "border_inactive": "#e6e6e6",
        "glyph": "#1a1a1a",
        "glyph_inactive": "#8a8a8a",
        "hover": "#000000",
        "hover_opacity": 0.06,
        "pressed_opacity": 0.03,
        "text": "26,26,26",
        "text_inactive": "130,130,130",
    },
}
CLOSE_HOVER = "#c42b1c"          # the one Windows 11 colour we copy: reference → window.close_hover
CLOSE_PRESSED = "#b0271a"

EDGE = 20                        # the stretched middle slices are 20 px; only the corners are fixed
SHADOW = {"top": 12, "bottom": 24, "side": 18}


def reference() -> dict:
    return json.loads(REFERENCE.read_text(encoding="utf-8"))["window"]


# --- decoration.svg ----------------------------------------------------------------------------
def _slice(name: str, x: int, y: int, w: int, h: int, fill: str, path: str | None = None) -> str:
    if path:
        return f'  <path id="{name}" d="{path}" fill="{fill}"/>\n'
    return f'  <rect id="{name}" x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}"/>\n'


def _corner(name: str, x: int, y: int, w: int, h: int, radius: int, fill: str, corner: str,
            border: str | None = None) -> str:
    """A corner slice whose outer angle is rounded.

    Drawn as two filled paths, never as a stroke: Aurorae scales each slice to the *bounding box*
    of its SVG element, and a stroke inflates that box by half its width, which shifts the whole
    decoration by half a pixel. Filled shapes keep the box exactly one slot big — the outer path
    is the frame colour, the inner path (inset by 1 px on the outer sides) is the fill.
    """
    r = radius
    b = 1 if border else 0

    def shape(ox: float, oy: float, ow: float, oh: float, rr: float) -> str:
        if corner == "topleft":
            return (f"M{ox},{oy + oh} L{ox},{oy + rr} Q{ox},{oy} {ox + rr},{oy} "
                    f"L{ox + ow},{oy} L{ox + ow},{oy + oh} Z")
        if corner == "topright":
            return (f"M{ox},{oy} L{ox + ow - rr},{oy} Q{ox + ow},{oy} {ox + ow},{oy + rr} "
                    f"L{ox + ow},{oy + oh} L{ox},{oy + oh} Z")
        if corner == "bottomleft":
            return (f"M{ox},{oy} L{ox + ow},{oy} L{ox + ow},{oy + oh} L{ox + rr},{oy + oh} "
                    f"Q{ox},{oy + oh} {ox},{oy + oh - rr} Z")
        return (f"M{ox},{oy} L{ox + ow},{oy} L{ox + ow},{oy + oh - rr} "
                f"Q{ox + ow},{oy + oh} {ox + ow - rr},{oy + oh} L{ox},{oy + oh} Z")

    outer = shape(x, y, w, h, r)
    if not border:
        return f'  <g id="{name}">\n    <path d="{outer}" fill="{fill}"/>\n  </g>\n'
    # the inner shape: pulled in by 1 px on the two outer sides of this corner
    dx = b if corner in ("topleft", "bottomleft") else 0
    dy = b if corner in ("topleft", "topright") else 0
    inner = shape(x + dx, y + dy, w - b if dx == 0 else w - b, h - b if dy == 0 else h - b,
                  max(r - b, 0))
    return (f'  <g id="{name}">\n'
            f'    <path d="{outer}" fill="{border}"/>\n'
            f'    <path d="{inner}" fill="{fill}"/>\n'
            f'  </g>\n')


def _edge_slice(name: str, x: int, y: int, w: int, h: int, fill: str, border: str,
                side: str) -> str:
    """A stretched edge slice: the window body plus the 1 px frame line on its outer side.

    The line is a filled 1 px rect, not a stroke, so the slice's bounding box stays exact.
    """
    line = {"left": (x, y, 1, h),
            "right": (x + w - 1, y, 1, h),
            "bottom": (x, y + h - 1, w, 1)}[side]
    return (f'  <g id="{name}">\n'
            f'    <rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}"/>\n'
            f'    <rect x="{line[0]}" y="{line[1]}" width="{line[2]}" height="{line[3]}" '
            f'fill="{border}"/>\n'
            f'  </g>\n')


def decoration_svg(palette: dict, window: dict) -> str:
    radius = window["corner_radius"]
    title = window["title_bar_height"]
    corner = max(radius + 4, 12)                 # fixed-size corner slice, never stretched
    width = corner * 2 + EDGE
    height = title + EDGE + corner
    out = ['<?xml version="1.0" encoding="UTF-8"?>\n',
           f'<svg xmlns="http://www.w3.org/2000/svg" width="{width * 2}" height="{height * 2}" '
           f'viewBox="0 0 {width * 2} {height * 2}">\n',
           "  <!-- Zaldros window decoration. Generated by tools/theme/make_aurorae.py from\n"
           "       system/theme/win11-reference.json; edit the numbers there, not this file. -->\n"]

    def block(prefix: str, ox: int, oy: int, title_fill: str, body_fill: str, border: str) -> None:
        # top row: the title bar, rounded at the outer corners
        out.append(_corner(f"{prefix}topleft", ox, oy, corner, title, radius, title_fill,
                           "topleft", border))
        out.append(_slice(f"{prefix}top", ox + corner, oy, EDGE, title, title_fill))
        out.append(_corner(f"{prefix}topright", ox + corner + EDGE, oy, corner, title, radius,
                           title_fill, "topright", border))
        # middle row: the window body with a hairline frame on both sides
        out.append(_edge_slice(f"{prefix}left", ox, oy + title, corner, EDGE, body_fill, border,
                               "left"))
        out.append(_slice(f"{prefix}center", ox + corner, oy + title, EDGE, EDGE, body_fill))
        out.append(_edge_slice(f"{prefix}right", ox + corner + EDGE, oy + title, corner, EDGE,
                               body_fill, border, "right"))
        # bottom row: rounded at the outer corners, same hairline
        base = oy + title + EDGE
        out.append(_corner(f"{prefix}bottomleft", ox, base, corner, corner, radius, body_fill,
                           "bottomleft", border))
        out.append(_edge_slice(f"{prefix}bottom", ox + corner, base, EDGE, corner, body_fill,
                               border, "bottom"))
        out.append(_corner(f"{prefix}bottomright", ox + corner + EDGE, base, corner, corner,
                           radius, body_fill, "bottomright", border))

    block("decoration-", 0, 0, palette["title"], palette["body"], palette["border"])
    block("decoration-inactive-", width, height, palette["title_inactive"], palette["body"],
          palette["border_inactive"])

    # Content margins: how far the window contents sit from the edge of the drawn decoration.
    out.append(f'  <rect id="hint-top-margin" x="0" y="0" width="1" height="{title}" '
               'fill="none"/>\n')
    for name, size in (("bottom", 1), ("left", 1), ("right", 1)):
        out.append(f'  <rect id="hint-{name}-margin" x="0" y="0" width="{size}" '
                   f'height="{size}" fill="none"/>\n')
    # A soft drop shadow, drawn by us rather than by KWin's blur, so an unfocused window is
    # visibly unfocused even without compositing effects.
    for name, opacity in (("shadow_active", 0.45), ("shadow_inactive", 0.25)):
        out.append(f'  <rect id="{name}" x="{width}" y="0" width="{EDGE}" height="{EDGE}" '
                   f'fill="#000000" opacity="{opacity}"/>\n')
    for edge, size in (("top", SHADOW["top"]), ("bottom", SHADOW["bottom"]),
                       ("left", SHADOW["side"]), ("right", SHADOW["side"])):
        out.append(f'  <rect id="shadow-hint-{edge}-margin" x="0" y="0" width="{size}" '
                   f'height="{size}" fill="none"/>\n')
    out.append("</svg>\n")
    return "".join(out)


# --- the caption buttons -------------------------------------------------------------------------
def _glyph(kind: str, w: int, h: int, size: int, colour: str) -> str:
    """Our own geometry: a line, a square, two squares, an X.

    Every stroke is snapped to a half-pixel grid.  A 1 px stroke whose centre sits on an integer
    coordinate is rendered as two 50 % rows, which is why the first version of these glyphs came
    out grey and fuzzy instead of the crisp white hairlines the reference shows.  Centres on
    ``*.5`` land inside exactly one device pixel.
    """
    # glyph box: `size` wide, snapped so the box edges fall on integer pixel boundaries
    left = round(w / 2 - size / 2)
    top = round(h / 2 - size / 2)
    right, bottom = left + size, top + size
    stroke = (f'stroke="{colour}" stroke-width="1" fill="none" '
              'stroke-linecap="butt" stroke-linejoin="miter"')
    if kind == "minimize":
        y = round(h / 2) - 0.5
        return f'    <line x1="{left}" y1="{y}" x2="{right}" y2="{y}" {stroke}/>\n'
    if kind == "maximize":
        # corner radius measured off a real Windows 11 capture: 8 px on a 239 px button
        # (Wikimedia Commons "Titlebar buttons"), i.e. ~1.5 px at a 46 px button
        return (f'    <rect x="{left + 0.5}" y="{top + 0.5}" width="{size - 1}" '
                f'height="{size - 1}" rx="1.5" {stroke}/>\n')
    if kind == "restore":
        off = 2                      # how far the back window peeks out; reference ≈ 2 px at 100 %
        fx, fy = left + 0.5, top + off + 0.5
        fw = size - 1 - off
        return (f'    <rect x="{fx}" y="{fy}" width="{fw}" height="{fw}" rx="1.5" {stroke}/>\n'
                f'    <path d="M{fx + off},{fy} V{fy - off + 1} '
                f'Q{fx + off},{fy - off} {fx + off + 1},{fy - off} '
                f'H{fx + fw + off - 1} Q{fx + fw + off},{fy - off} {fx + fw + off},{fy - off + 1} '
                f'V{fy + fw - off} H{fx + fw}" {stroke}/>\n')
    if kind == "close":
        # the diagonals are antialiased whatever we do, so they run the full glyph box:
        # the reference X measures 10 px across at 100 %, corner to corner
        a, b = left, top
        c, d = right, bottom
        return (f'    <line x1="{a}" y1="{b}" x2="{c}" y2="{d}" {stroke}/>\n'
                f'    <line x1="{c}" y1="{b}" x2="{a}" y2="{d}" {stroke}/>\n')
    if kind == "alldesktops":
        return (f'    <circle cx="{left + size / 2}" cy="{top + size / 2}" r="{size / 2 - 0.5}" '
                f'{stroke}/>\n')
    if kind == "keepabove":
        return (f'    <path d="M{left + 0.5},{bottom - 3.5} L{left + size / 2},{top + 2.5} '
                f'L{right - 0.5},{bottom - 3.5}" {stroke}/>\n')
    return (f'    <path d="M{left + 0.5},{top + 3.5} L{left + size / 2},{bottom - 2.5} '
            f'L{right - 0.5},{top + 3.5}" {stroke}/>\n')


def button_svg(kind: str, palette: dict, window: dict) -> str:
    w = window["caption_button_width"]
    h = window["caption_button_height"]
    size = window["caption_glyph"]
    states = ("active", "hover", "pressed", "deactivated", "inactive")
    out = ['<?xml version="1.0" encoding="UTF-8"?>\n',
           f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h * len(states)}" '
           f'viewBox="0 0 {w} {h * len(states)}">\n',
           f"  <!-- Zaldros caption button ({kind}); generated by tools/theme/make_aurorae.py -->\n"]
    for index, state in enumerate(states):
        y = index * h
        colour = palette["glyph"]
        background = ""
        if state == "hover":
            if kind == "close":
                background = (f'    <rect x="0" y="0" width="{w}" height="{h}" '
                              f'fill="{CLOSE_HOVER}"/>\n')
                colour = "#ffffff"
            else:
                background = (f'    <rect x="0" y="0" width="{w}" height="{h}" '
                              f'fill="{palette["hover"]}" opacity="{palette["hover_opacity"]}"/>\n')
        elif state == "pressed":
            if kind == "close":
                background = (f'    <rect x="0" y="0" width="{w}" height="{h}" '
                              f'fill="{CLOSE_PRESSED}"/>\n')
                colour = "#ffffff"
            else:
                background = (f'    <rect x="0" y="0" width="{w}" height="{h}" '
                              f'fill="{palette["hover"]}" '
                              f'opacity="{palette["pressed_opacity"]}"/>\n')
        elif state in ("inactive", "deactivated"):
            colour = palette["glyph_inactive"]
        out.append(f'  <g id="{state}-center" transform="translate(0,{y})">\n')
        # Aurorae scales each state to the *bounding box* of its element. Without a full-size
        # frame the box collapses to the glyph itself and a 10 px X is stretched over the whole
        # 46 × 32 button — which is exactly what boot run 33113315031 showed. This invisible
        # rect keeps every state exactly one button big.
        out.append(f'    <rect x="0" y="0" width="{w}" height="{h}" fill="#000000" '
                   'fill-opacity="0"/>\n')
        out.append(background)
        out.append(_glyph(kind, w, h, size, colour))
        out.append("  </g>\n")
    out.append("</svg>\n")
    return "".join(out)


# --- the theme -------------------------------------------------------------------------------
def theme_rc(name: str, palette: dict, window: dict) -> str:
    title = window["title_bar_height"]
    return f"""[General]
ActiveTextColor={palette["text"]}
InactiveTextColor={palette["text_inactive"]}
TitleAlignment=Left
TitleVerticalAlignment=Center
UseTextShadow=false
Shadow=true
Animation=100
LeftButtons=
RightButtons=IAX

[Layout]
BorderLeft=1
BorderRight=1
BorderBottom=1

ButtonWidth={window["caption_button_width"]}
ButtonWidthClose={window["caption_button_width"]}
ButtonWidthMaximizeRestore={window["caption_button_width"]}
ButtonWidthMinimize={window["caption_button_width"]}
ButtonHeight={window["caption_button_height"]}
ButtonSpacing=0
ButtonMarginTop=0
ExplicitButtonSpacer=0

PaddingTop={SHADOW["top"]}
PaddingBottom={SHADOW["bottom"]}
PaddingLeft={SHADOW["side"]}
PaddingRight={SHADOW["side"]}

TitleEdgeTop=0
TitleEdgeBottom=0
TitleEdgeLeft={window["title_left_margin"]}
TitleEdgeRight=0
TitleBorderLeft=0
TitleBorderRight=0
TitleHeight={title}
TitleEdgeTopMaximized=0
TitleEdgeBottomMaximized=0
TitleEdgeLeftMaximized={window["title_left_margin"]}
TitleEdgeRightMaximized=0
"""


def metadata(name: str) -> str:
    return f"""[Desktop Entry]
Name={name}
Comment=Zaldros window decoration, generated from the measured Windows 11 geometry
X-KDE-PluginInfo-Author=Zaldros
X-KDE-PluginInfo-Name={name}
X-KDE-PluginInfo-Version=1.0
X-KDE-PluginInfo-License=GPL-3.0-or-later
X-KDE-PluginInfo-EnabledByDefault=true
"""


BUTTONS = ("close", "maximize", "restore", "minimize", "alldesktops", "keepabove", "keepbelow")


def write_theme(name: str, out_dir: Path, window: dict) -> list[Path]:
    palette = PALETTES[name]
    directory = out_dir / name
    directory.mkdir(parents=True, exist_ok=True)
    written = []
    for filename, body in [("decoration.svg", decoration_svg(palette, window)),
                           (f"{name}rc", theme_rc(name, palette, window)),
                           ("metadata.desktop", metadata(name))]:
        path = directory / filename
        path.write_text(body, encoding="utf-8")
        written.append(path)
    for kind in BUTTONS:
        path = directory / f"{kind}.svg"
        path.write_text(button_svg(kind, palette, window), encoding="utf-8")
        written.append(path)
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(REPO / "assets" / "themes" / "aurorae"))
    args = parser.parse_args()
    window = reference()
    for name in PALETTES:
        files = write_theme(name, Path(args.out), window)
        print(f"{name}: {len(files)} files -> {Path(args.out) / name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
