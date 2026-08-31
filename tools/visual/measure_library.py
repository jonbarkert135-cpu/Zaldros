"""Measure Windows 11 geometry from the public reference library.

Every number in system/theme/win11-reference.json used to come from captures that cannot be
published: the maintainer's own screenshots. This tool re-derives the same values from Microsoft's
own published screenshots (assets/refs/win11/library.json), so the parity reference can be checked
by anyone who runs:

    python3 tools/visual/fetch_references.py
    python3 tools/visual/measure_library.py            # measure and compare with the reference
    python3 tools/visual/measure_library.py --json     # machine-readable

Only captures whose display scale can be proven are measured:

* quick-access-update2.png — File Explorer with a file context menu. The three caption glyphs sit
  46 px apart, which is the Windows 11 caption button width in logical pixels, so this capture is
  at 100 % scale and pixels are logical pixels.
* WIN11_22H2_...SnapLayouts...1920.png — the 22H2 snap bar. Its taskbar is 47 px tall against a
  documented 48, so the capture is at 100 % scale and the snap thumbnails are logical pixels.
* color-profile-quick-settings.png — the Quick Settings flyout. Its panel is 538 px wide against a
  documented 360 logical px, i.e. 150 % scale; every other value in the panel is divided by 1.5.

The script exits non-zero when a measurement disagrees with win11-reference.json beyond that
component's tolerance. It exits 2 — loudly, never silently — when the cache is missing.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIBRARY = ROOT / "assets" / "refs" / "win11" / "library.json"
CACHE = ROOT / "assets" / "refs" / "win11" / "cache"
REFERENCE = ROOT / "system" / "theme" / "win11-reference.json"

EXPLORER = "quick-access-update2.png"
QUICK = "color-profile-quick-settings.png"
SNAP = "WIN11_22H2_CML_JIT_TouchAssist_SnapLayouts_Flow-1_HERO_16x9_en-US_1920.png"
TASKBAR_LOGICAL_HEIGHT = 48.0         # win11-reference.json → taskbar.height
QUICK_PANEL_LOGICAL_WIDTH = 360.0     # win11-reference.json → quick_settings.width


@dataclass
class Measurement:
    source: str
    metric: str
    logical: float
    reference: float | None
    tolerance: float | None

    @property
    def checked(self) -> bool:
        return self.reference is not None

    @property
    def passed(self) -> bool:
        if not self.checked:
            return True
        return abs(self.logical - self.reference) <= (self.tolerance or 0)

    def line(self) -> str:
        if not self.checked:
            return f"----  {self.source:<34} {self.metric:<26} {self.logical:>7.1f}   (new)"
        mark = "PASS" if self.passed else "FAIL"
        return (f"{mark}  {self.source:<34} {self.metric:<26} {self.logical:>7.1f}   "
                f"reference {self.reference:>6.1f}")


def _numpy():
    try:
        import numpy as np
        from PIL import Image
    except ImportError as error:                            # pragma: no cover - environment issue
        raise SystemExit(f"measure_library needs numpy and pillow: {error}")
    return np, Image


def _runs(indices, join: int) -> list[tuple[int, int]]:
    groups: list[tuple[int, int]] = []
    for value in indices:
        value = int(value)
        if groups and value - groups[-1][1] <= join:
            groups[-1] = (groups[-1][0], value)
        else:
            groups.append((value, value))
    return groups


def measure_explorer(path: Path) -> list[Measurement]:
    """File Explorer at 100 % scale: caption buttons and the context menu row pitch."""
    np, Image = _numpy()
    image = np.asarray(Image.open(path).convert("RGB")).astype(int)
    light = image.min(axis=2) > 230
    rows = np.where(light.sum(axis=1) > 500)[0]
    cols = np.where(light.sum(axis=0) > 300)[0]
    top, right = int(rows.min()), int(cols.max())

    # caption glyphs: dark ink in the title band, right-hand 400 px
    band = image[top:top + 60, right - 400:right]
    ink = (band.min(axis=2) < 120).sum(axis=0)
    glyphs = _runs(np.where(ink > 0)[0], join=6)
    centres = [(start + end) / 2 for start, end in glyphs]
    pitches = [centres[i + 1] - centres[i] for i in range(len(centres) - 1)]
    caption_pitch = float(np.median(pitches)) if pitches else float("nan")

    # context menu: text rows inside the menu plate on the right half of the file list
    menu = image[600:760, 620:820]
    dark = (menu.min(axis=2) < 120).sum(axis=1)
    bands = _runs(np.where(dark > 2)[0], join=4)
    menu_centres = [(start + end) / 2 for start, end in bands]
    menu_pitches = [menu_centres[i + 1] - menu_centres[i] for i in range(len(menu_centres) - 1)]
    item_height = float(np.median(menu_pitches)) if menu_pitches else float("nan")

    reference = json.loads(REFERENCE.read_text())
    return [
        Measurement(EXPLORER, "caption button width", round(caption_pitch, 1),
                    reference["window"]["caption_button_width"], 2.0),
        Measurement(EXPLORER, "context menu item height", round(item_height, 1),
                    reference["context_menu"]["item_height"], 1.0),
    ]


def measure_quick_settings(path: Path) -> list[Measurement]:
    """Quick Settings flyout; scale is derived from the documented 360 px panel width."""
    np, Image = _numpy()
    image = np.asarray(Image.open(path).convert("RGB")).astype(int)

    def runs_of(mask, join: int = 4, minimum: int = 8) -> list[tuple[int, int]]:
        return [run for run in _runs(np.where(mask)[0], join) if run[1] - run[0] >= minimum]

    # The panel is the light plate; y=720 crosses it below the sliders, where it is uninterrupted.
    plate = runs_of(image[720].min(axis=1) > 190, join=2, minimum=100)
    panel_left, panel_right = plate[0]
    panel_width = panel_right - panel_left
    scale = panel_width / QUICK_PANEL_LOGICAL_WIDTH

    # y=143 crosses the first row of tiles; anything that differs from the plate colour is a tile.
    panel_bg = image[143, panel_left + 8]
    tile_row = image[143, panel_left:panel_right]
    tiles = runs_of(np.abs(tile_row - panel_bg).sum(axis=1) > 25, join=6, minimum=40)
    padding = tiles[0][0]
    tile_width = tiles[0][1] - tiles[0][0]
    tile_gap = tiles[1][0] - tiles[0][1]

    centre = panel_left + (tiles[0][0] + tiles[0][1]) // 2
    column = np.abs(image[:, centre] - panel_bg).sum(axis=1) > 25
    tile_top, tile_bottom = [run for run in runs_of(column, join=4, minimum=20) if run[0] > 80][0]
    tile_height = tile_bottom - tile_top

    reference = json.loads(REFERENCE.read_text())["quick_settings"]
    tolerance = float(reference["tolerance"])
    return [
        Measurement(QUICK, "display scale", round(scale, 3), None, None),
        Measurement(QUICK, "panel width", round(panel_width / scale, 1),
                    reference["width"], tolerance),
        Measurement(QUICK, "panel padding", round(padding / scale, 1),
                    reference["padding"], tolerance),
        Measurement(QUICK, "tile width", round(tile_width / scale, 1),
                    reference["tile_width"], tolerance),
        Measurement(QUICK, "tile height", round(tile_height / scale, 1),
                    reference["tile_height"], tolerance),
        Measurement(QUICK, "tile gap", round(tile_gap / scale, 1),
                    reference["tile_gap"], tolerance),
    ]


def measure_snap_bar(path: Path) -> list[Measurement]:
    """The snap bar: six layout thumbnails.

    The capture is proven to be at 100 % scale by its own taskbar (48 logical px), so the
    thumbnails are measured in raw pixels — no scale division that could hide a drift.
    """
    np, Image = _numpy()
    image = np.asarray(Image.open(path).convert("RGB")).astype(int)
    height = image.shape[0]

    # Taskbar: the flat band at the bottom of the left edge, away from every window.
    column = image[:, 5]
    edge = column[-1]
    taskbar_top = height - 1
    while taskbar_top > height - 120 and np.abs(column[taskbar_top] - edge).sum() < 40:
        taskbar_top -= 1
    taskbar_height = height - 1 - taskbar_top

    # The thumbnails are flat mid-grey plates (the selected one is the accent blue).
    grey = image.mean(axis=2)
    saturation = image.max(axis=2) - image.min(axis=2)
    cells = ((grey > 50) & (grey < 110) & (saturation < 20)) | \
            ((image[:, :, 2] > 200) & (image[:, :, 0] < 150))

    # A row through the upper half of the bar: every run is one thumbnail column.
    runs = [run for run in _runs(np.where(cells[40])[0], join=1) if run[1] - run[0] >= 15]
    # Group runs into layouts: inside a thumbnail the gap is the cell gap, between thumbnails wider.
    gaps = [runs[i + 1][0] - runs[i][1] for i in range(len(runs) - 1)]
    split = (min(gaps) + max(gaps)) / 2
    layouts: list[list[tuple[int, int]]] = [[runs[0]]]
    for index, gap in enumerate(gaps):
        (layouts.append([runs[index + 1]]) if gap > split
         else layouts[-1].append(runs[index + 1]))

    thumb_widths = [group[-1][1] - group[0][0] + 1 for group in layouts]
    thumb_gaps = [layouts[i + 1][0][0] - layouts[i][-1][1] - 1 for i in range(len(layouts) - 1)]
    cell_gaps = [group[i + 1][0] - group[i][1] - 1
                 for group in layouts for i in range(len(group) - 1)]

    # Thumbnail height from the last layout, the one no window overlaps in this capture.
    centre = (layouts[-1][0][0] + layouts[-1][0][1]) // 2
    top, bottom = [run for run in _runs(np.where(cells[:, centre])[0], join=1)
                   if run[1] - run[0] >= 20][0]

    # Panel: the dark plate behind the thumbnails, matched by its own colour on the row above them
    # — matching "anything but the wallpaper" also catches the windows behind the bar.
    above = top - 6
    first, last = layouts[0][0][0], layouts[-1][-1][1]
    same = np.abs(image[above] - image[above, first + 2]).sum(axis=1) < 30
    panel = [run for run in _runs(np.where(same)[0], join=2) if run[0] <= first + 2 <= run[1]][0]

    reference = json.loads(REFERENCE.read_text())["snap_layouts"]
    tolerance = float(reference["tolerance"])

    # The zones themselves: a thumbnail's column widths divided by its content width are the
    # fractions of the screen each zone gets. This is where the six layouts come from.
    zone_checks: list[Measurement] = []
    for index, group in enumerate(layouts):
        content = (group[-1][1] - group[0][0] + 1) - reference["cell_gap"] * (len(group) - 1)
        measured = [round((end - start + 1) / content, 3) for start, end in group]
        expected = sorted({(zone[0], zone[2]) for zone in reference["zones"][index]})
        zone_checks.append(Measurement(
            SNAP, f"layout {index + 1} columns",
            float(len(measured)), float(len(expected)), 0.0))
        for column, ((_, width), fraction) in enumerate(zip(expected, measured)):
            zone_checks.append(Measurement(
                SNAP, f"layout {index + 1} column {column + 1}",
                fraction, round(width, 3), 0.02))

    return zone_checks + [
        Measurement(SNAP, "taskbar height (scale proof)", float(taskbar_height),
                    TASKBAR_LOGICAL_HEIGHT, 2.0),
        Measurement(SNAP, "layouts", float(len(layouts)), reference["layouts"], 0.0),
        Measurement(SNAP, "thumb width", float(np.median(thumb_widths)),
                    reference["thumb_width"], tolerance),
        Measurement(SNAP, "thumb height", float(bottom - top + 1),
                    reference["thumb_height"], tolerance),
        Measurement(SNAP, "thumb gap", float(np.median(thumb_gaps)),
                    reference["thumb_gap"], tolerance),
        Measurement(SNAP, "cell gap", float(np.median(cell_gaps)),
                    reference["cell_gap"], tolerance),
        Measurement(SNAP, "panel padding", float(first - panel[0]),
                    reference["padding"], tolerance),
        Measurement(SNAP, "panel width", float(panel[1] - panel[0] + 1),
                    reference["panel_width"], tolerance),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    needed = [EXPLORER, QUICK, SNAP]
    absent = [name for name in needed if not (CACHE / name).exists()]
    if absent:
        print("reference cache incomplete: " + ", ".join(absent), file=sys.stderr)
        print("run: python3 tools/visual/fetch_references.py", file=sys.stderr)
        return 2

    measurements = (measure_explorer(CACHE / EXPLORER)
                    + measure_quick_settings(CACHE / QUICK)
                    + measure_snap_bar(CACHE / SNAP))
    if args.json:
        print(json.dumps([asdict(m) for m in measurements], indent=2))
    else:
        for measurement in measurements:
            print(measurement.line())
    failures = [m for m in measurements if not m.passed]
    if not args.json:
        print(f"\n{len(measurements) - len(failures)}/{len(measurements)} measurements agree with "
              f"system/theme/win11-reference.json")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
