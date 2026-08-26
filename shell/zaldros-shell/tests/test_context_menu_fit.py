"""A context menu must never draw a label through its shortcut.

Run #35 compared the rendered desktop menu with the real Windows 11 menus in the reference library
(assets/refs/win11/library.json) and found the Russian row "Показать дополнительные параметры"
printed straight over "Shift+F10": the menu width was pinned at 300 px whatever the language, while
Windows 11 grows a menu to fit its widest row.

The gate below is deliberately pixel-based, not a re-run of the layout arithmetic: it renders the
menu state, walks every item row of the crop and demands a clear background gutter between the last
text block on a row (the shortcut or the submenu chevron) and everything to its left.
"""
import os
import sys
from pathlib import Path

import pytest

pytest.importorskip("PySide6")
pytest.importorskip("PIL")
pytest.importorskip("numpy")

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shell" / "zaldros-shell"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

MIN_GUTTER = 8      # px of background required between a label and its shortcut
ROW_HEIGHT = 32     # win11-reference.json → context_menu.item_height
PADDING = 4         # win11-reference.json → context_menu.padding


@pytest.fixture(scope="module")
def menu_crop(tmp_path_factory):
    from zaldros_shell.app import render
    import json

    directory = tmp_path_factory.mktemp("menu")
    png = directory / "menu.png"
    geometry_file = directory / "menu.geometry.json"
    render(str(png), width=1600, height=1000, context_open=True,
           geometry_output=str(geometry_file))
    box = json.loads(geometry_file.read_text())["items"]["contextMenu"]
    image = Image.open(png).convert("RGB")
    crop = image.crop((box["left"], box["top"],
                       box["left"] + box["width"], box["top"] + box["height"]))
    return np.asarray(crop).astype(int)


def _text_runs(row: np.ndarray, background: np.ndarray) -> list[tuple[int, int]]:
    """Column runs whose pixels differ from the menu background — i.e. glyphs."""
    ink = (np.abs(row - background).sum(axis=2) > 60).any(axis=0)
    runs: list[tuple[int, int]] = []
    for x in np.where(ink)[0]:
        if runs and x - runs[-1][1] <= 5:      # 5 px joins glyphs inside one word
            runs[-1] = (runs[-1][0], int(x))
        else:
            runs.append((int(x), int(x)))
    return runs


def test_no_menu_row_draws_a_label_through_its_shortcut(menu_crop):
    height, width, _ = menu_crop.shape
    # Sample the background two pixels inside the frame: the menu paints a 1 px border, and a
    # border pixel taken for "background" makes every empty pixel read as ink.
    background = menu_crop[height // 2, width - 8]
    collisions = []
    for top in range(PADDING, height - PADDING - ROW_HEIGHT + 1, ROW_HEIGHT):
        row = menu_crop[top + 4:top + ROW_HEIGHT - 4, 2:width - 2]
        runs = _text_runs(row, background)
        if len(runs) < 2:
            continue
        last_start, last_end = (runs[-1][0] + 2, runs[-1][1] + 2)
        if last_end < width - 40:                       # nothing sitting on the right edge
            continue
        gutter = last_start - (runs[-2][1] + 2)
        if gutter < MIN_GUTTER:
            collisions.append(f"row at y={top}: gutter {gutter}px before the trailing text")
    assert not collisions, "context menu text overlaps:\n" + "\n".join(collisions)


def test_no_menu_text_touches_the_right_margin(menu_crop):
    """Windows 11 keeps a 12 px margin between the last glyph and the menu edge.

    Sampling starts two pixels inside the frame: the menu draws its own 1 px border and rounds its
    corners, and antialiasing on that border is not text.
    """
    height, width, _ = menu_crop.shape
    background = menu_crop[height // 2, width - 8]
    overruns = []
    for top in range(PADDING, height - PADDING - ROW_HEIGHT + 1, ROW_HEIGHT):
        row = menu_crop[top + 4:top + ROW_HEIGHT - 4, 2:width - 2]
        runs = _text_runs(row, background)
        if not runs:
            continue
        right = runs[-1][1] + 2
        if right > width - 8:
            overruns.append(f"row at y={top}: last glyph at x={right} of {width}")
    assert not overruns, "context menu draws text into its right margin:\n" + "\n".join(overruns)
