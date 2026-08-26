"""Measure Windows 11 geometry from the reference screenshot.

The only Windows 11 artefact in this repository is `assets/refs/win11_start_reference.png`, a
1920x1280 capture of a real Windows 11 desktop with Start open. It is used as a *ruler*: this
script measures edges and icon positions in it and writes the numbers to
`system/theme/win11-reference.json`. Nothing is copied from the image into the product; the shell
is drawn from our own components and only the measurements travel.

The capture runs at 125 % display scaling (its taskbar is 60 px tall and Windows 11 draws a 48 px
taskbar at 100 %), so every measured pixel value is divided by 1.25 to get the logical value the
shell has to reproduce.

Run:  python3 tools/visual/measure_reference.py [--check]
`--check` re-measures and fails when the committed JSON no longer matches the screenshot.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
REFERENCE_PNG = ROOT / "assets" / "refs" / "win11_start_reference.png"
OUTPUT_JSON = ROOT / "system" / "theme" / "win11-reference.json"
SCALE = 1.25  # the capture is a 125 % display


class Ruler:
    def __init__(self, path: Path) -> None:
        self.image = Image.open(path).convert("RGB")
        self.width, self.height = self.image.size
        self.px = self.image.load()

    # --- primitives ---------------------------------------------------------------------
    def _delta(self, a, b) -> int:
        return sum(abs(a[i] - b[i]) for i in range(3))

    def row_edges(self, y: int, x0: int, x1: int, threshold: int = 40) -> list[int]:
        return [x for x in range(x0 + 1, x1)
                if self._delta(self.px[x - 1, y], self.px[x, y]) > threshold]

    def column_edges(self, x: int, y0: int, y1: int, threshold: int = 40) -> list[int]:
        return [y for y in range(y0 + 1, y1)
                if self._delta(self.px[x, y - 1], self.px[x, y]) > threshold]

    def coloured_bands(self, y0: int, y1: int, x0: int, x1: int,
                       min_width: int = 8) -> list[tuple[int, int]]:
        """Horizontal extents of saturated artwork (application icons) inside a band."""
        bands: list[tuple[int, int]] = []
        start = None
        for x in range(x0, x1):
            lit = 0
            for y in range(y0, y1):
                colour = self.px[x, y]
                if max(colour) > 90 and max(colour) - min(colour) > 60:
                    lit += 1
            if lit > 2 and start is None:
                start = x
            elif lit <= 2 and start is not None:
                if x - start >= min_width:
                    bands.append((start, x - 1))
                start = None
        return bands

    def icon_rows(self, y0: int, y1: int, x0: int, x1: int) -> list[tuple[int, int]]:
        """Vertical extents of the rows of application artwork inside a region."""
        rows: list[tuple[int, int]] = []
        start = None
        for y in range(y0, y1):
            lit = 0
            for x in range(x0, x1, 2):
                colour = self.px[x, y]
                if max(colour) > 90 and max(colour) - min(colour) > 60:
                    lit += 1
            if lit > 5 and start is None:
                start = y
            elif lit <= 5 and start is not None:
                if y - start > 10:
                    rows.append((start, y - 1))
                start = None
        return rows


def cluster(values: list[int], gap: int = 3) -> list[int]:
    """Collapse runs of adjacent edge pixels (anti-aliasing) into one coordinate each."""
    groups: list[list[int]] = []
    for value in values:
        if groups and value - groups[-1][-1] <= gap:
            groups[-1].append(value)
        else:
            groups.append([value])
    return [round(sum(group) / len(group)) for group in groups]


def logical(value: float) -> float:
    return round(value / SCALE, 1)




def measure(ruler: Ruler) -> dict:
    height = ruler.height
    width = ruler.width

    # --- taskbar --------------------------------------------------------------------------
    # The bar is the bottom band whose top edge is visible across the whole width.
    taskbar_top = max(y for y in ruler.column_edges(100, height - 120, height, 60))
    taskbar_height = height - taskbar_top

    # centred application group: saturated icon blobs in the lower band
    icons = ruler.coloured_bands(taskbar_top + 6, height - 6, 600, 1400, min_width=6)
    centres = [(a + b) / 2 for a, b in icons]
    pitches = [round(centres[i + 1] - centres[i], 1) for i in range(len(centres) - 1)]
    typical_pitch = sorted(pitches)[len(pitches) // 2]
    icon_widths = sorted(b - a + 1 for a, b in icons)
    typical_icon = icon_widths[len(icon_widths) // 2]

    # --- Start panel ----------------------------------------------------------------------
    row = taskbar_top - 70                       # inside the footer strip, away from content
    panel_edges = ruler.row_edges(row, 400, 1500, 60)
    panel_left, panel_right = panel_edges[0], panel_edges[-1]
    column = panel_left + 20
    vertical = ruler.column_edges(column, 250, taskbar_top, 60)
    panel_top, panel_bottom = vertical[0], vertical[-1]
    footer_top = max(y for y in vertical if y < panel_bottom - 40)

    # --- search field inside Start ----------------------------------------------------------
    search_column = panel_right - 160
    search_edges = cluster(ruler.column_edges(search_column, panel_top + 10, panel_top + 150, 18))
    search_top, search_bottom = search_edges[0], search_edges[1]
    search_row = (search_top + search_bottom) // 2
    field = ruler.row_edges(search_row, panel_left + 10, panel_right - 10, 18)
    search_left, search_right = field[0], field[-1]

    # --- pinned grid --------------------------------------------------------------------------
    grid_top, grid_bottom = panel_top + 150, panel_top + 500
    icon_rows = ruler.icon_rows(grid_top, grid_bottom, panel_left + 20, panel_right - 20)
    first_row = ruler.coloured_bands(icon_rows[0][0], icon_rows[0][1], panel_left + 20,
                                     panel_right - 20, min_width=12)
    pin_centres = [(a + b) / 2 for a, b in first_row]
    pin_pitch = round((pin_centres[-1] - pin_centres[0]) / max(len(pin_centres) - 1, 1), 1)
    pin_icon = sorted(b - a + 1 for a, b in first_row)[len(first_row) // 2]
    row_tops = [top for top, _ in icon_rows]
    row_pitch = round((row_tops[-1] - row_tops[0]) / max(len(row_tops) - 1, 1), 1)

    return {
        "source": {
            "file": "assets/refs/win11_start_reference.png",
            "capture": f"{width}x{height}",
            "display_scale": SCALE,
            "note": "every value below is logical (100 % scale): measured pixels / display_scale",
        },
        "taskbar": {
            "height": logical(taskbar_height),
            "icon": logical(typical_icon),
            "button_pitch": logical(typical_pitch),
            "group_alignment": "centred",
        },
        "start": {
            "width": logical(panel_right - panel_left),
            "height": logical(panel_bottom - panel_top),
            "gap_above_taskbar": logical(taskbar_top - panel_bottom),
            "padding": logical(search_left - panel_left),
            "alignment": "centred",
            "search_width": logical(search_right - search_left),
            "search_height": logical(search_bottom - search_top),
            "search_top_inset": logical(search_top - panel_top),
            "footer_height": logical(panel_bottom - footer_top),
            "pin_columns": len(first_row),
            "pin_cell_width": logical(pin_pitch),
            "pin_cell_height": logical(row_pitch),
            # the saturated-pixel span of the artwork; Windows lays it out in a 32 px box
            "pin_icon_artwork": logical(pin_icon),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="fail when the committed JSON differs from a fresh measurement")
    args = parser.parse_args()

    ruler = Ruler(REFERENCE_PNG)
    measured = measure(ruler)

    if args.check:
        committed = json.loads(OUTPUT_JSON.read_text())
        for section in ("taskbar", "start"):
            for key, value in measured[section].items():
                stored = committed[section].get(key, {})
                stored_value = stored.get("value") if isinstance(stored, dict) else stored
                if isinstance(value, (int, float)) and isinstance(stored_value, (int, float)):
                    if abs(value - stored_value) > 2.0:   # 1 px of anti-aliasing at 125 % = 1.6
                        print(f"MISMATCH {section}.{key}: measured {value}, committed {stored_value}")
                        return 1
        print("reference JSON matches the screenshot")
        return 0

    print(json.dumps(measured, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
