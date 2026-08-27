"""The Sheets window is measured, not eyeballed.

Every number checked here comes from system/theme/excel-reference.json, which in turn records
where each measurement came from in Microsoft's own Excel captures. If the QML drifts from the
reference, this fails; if the reference changes, the QML has to follow.
"""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")

from zaldros_sheets.model import column_name, reference  # noqa: E402

REF = reference()
WIDTH, HEIGHT = 1280, 800


@pytest.fixture(scope="module")
def shot(tmp_path_factory):
    from zaldros_sheets.app import render

    out = tmp_path_factory.mktemp("sheets") / "light.png"
    render(str(out), light=True, width=WIDTH, height=HEIGHT)
    from PySide6.QtGui import QImage

    image = QImage(str(out))
    assert not image.isNull(), "the render produced no image"
    return image


def band_bottom(image, top: int, x: int) -> int:
    """First row below `top` whose colour differs from the colour at `top`."""
    start = image.pixelColor(x, top).rgb()
    for y in range(top + 1, image.height()):
        if image.pixelColor(x, y).rgb() != start:
            return y
    return image.height()


def test_the_title_bar_is_the_measured_height_and_the_measured_green(shot):
    palette = REF["palette"]["light"]
    x = 1120  # green, clear of the centred title text and of the caption buttons
    assert shot.pixelColor(x, 4).name() == palette["title"]
    assert band_bottom(shot, 0, x) == REF["window"]["title_bar_height"]


def test_the_ribbon_card_starts_after_the_tab_strip(shot):
    window = REF["window"]
    top = window["title_bar_height"]
    # the tab strip is the strip colour; the card is the card colour
    assert shot.pixelColor(1240, top + 4).name() == REF["palette"]["light"]["tab_strip"]
    card_top = top + window["tab_strip_height"]
    assert shot.pixelColor(640, card_top + 6).name() == REF["palette"]["light"]["ribbon_card"]


def test_the_grid_rows_are_twenty_pixels_like_excel(shot):
    """Find the column-header band, then step down whole rows and land on gridlines."""
    grid = REF["grid"]
    header = REF["palette"]["light"]["header"]
    header_top = None
    for y in range(200, 400):
        if shot.pixelColor(600, y).name() == header:
            header_top = y
            break
    assert header_top is not None, "no column-header band found"
    first_row_top = header_top + grid["column_header_height"]
    gridline = REF["palette"]["light"]["gridline"]
    for step in (1, 2, 3):
        y = first_row_top + step * grid["row_height"] - 1
        assert shot.pixelColor(600, y).name() == gridline, (
            f"row {step} does not end on a gridline at y={y}")


def test_the_row_header_is_the_measured_width(shot):
    grid = REF["grid"]
    palette = REF["palette"]["light"]
    y = None
    for candidate in range(260, 400):
        if shot.pixelColor(4, candidate).name() == palette["header"]:
            y = candidate
            break
    assert y is not None, "no row-header band found"
    assert shot.pixelColor(grid["row_header_width"] - 2, y).name() == palette["header"]
    assert shot.pixelColor(grid["row_header_width"] + 4, y).name() != palette["header"]


def test_column_names_follow_excel(): 
    assert [column_name(i) for i in (0, 25, 26, 27, 51, 52)] == \
        ["A", "Z", "AA", "AB", "AZ", "BA"]


def test_the_status_bar_says_when_no_workbook_is_open(tmp_path):
    """An empty window must say it is empty rather than look like a loaded file."""
    from zaldros_sheets.app import _open

    engine, workbook, status = _open(None)
    assert engine is None and workbook is None
    assert "No workbook open" in status
