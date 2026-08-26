"""Visual regression tests: the shell must actually render, and the rendered pixels must match the
geometry we claim (spec PART 5 §8, VISUAL FOUNDATION §14).

Skipped when PySide6 is unavailable so the rest of the suite still runs; CI installs PySide6.
"""
import os
import sys

import pytest

pytest.importorskip("PySide6")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QImage  # noqa: E402

from zaldros_shell.app import render  # noqa: E402

W, H = 1600, 1000
TASKBAR_HEIGHT = 48


def shot(tmp_path, name, **kwargs):
    return render(str(tmp_path / f"{name}.png"), width=W, height=H, **kwargs)


@pytest.fixture(scope="module")
def desktop(tmp_path_factory):
    return shot(tmp_path_factory.mktemp("shots"), "desktop")


def test_desktop_renders_at_the_requested_size(desktop):
    image = QImage(desktop)
    assert (image.width(), image.height()) == (W, H)


def test_taskbar_band_is_drawn_at_the_documented_height(desktop):
    """A 48 px bar of the measured Windows 11 colour must exist.

    Brightness alone cannot prove it: the bar is #222222 and a dark wallpaper can be just as dark.
    What is provable is that the band is a flat fill of that colour while the row above it is not.
    """
    image = QImage(desktop)
    row = H - TASKBAR_HEIGHT // 2
    band = [image.pixelColor(x, row) for x in range(10, 200, 10)]
    assert all(colour.lightness() < 110 for colour in band), "taskbar band is not dark"
    # the bar is 95 % opaque over the wallpaper, so a couple of levels of variation are expected
    spread = max(colour.lightness() for colour in band) - min(colour.lightness() for colour in band)
    assert spread <= 4, f"taskbar band is not a flat fill (spread {spread})"
    above = [image.pixelColor(x, H - TASKBAR_HEIGHT - 30).lightness() for x in range(10, 200, 10)]
    assert max(above) - min(above) > spread, "the wallpaper row looks like the taskbar"


def test_start_button_and_tray_occupy_the_expected_zones(desktop):
    """Windows 11 places the Start group centred and the clock at the right edge."""
    image = QImage(desktop)
    row = H - TASKBAR_HEIGHT // 2
    centre = [image.pixelColor(x, row).lightness() for x in range(W // 2 - 200, W // 2 + 200)]
    right = [image.pixelColor(x, row).lightness() for x in range(W - 200, W - 10)]
    assert max(centre) - min(centre) > 40, "nothing is drawn in the centre group"
    assert max(right) - min(right) > 30, "tray area looks empty"


def test_opening_start_changes_the_screen(tmp_path):
    closed, opened = QImage(shot(tmp_path, "c")), QImage(shot(tmp_path, "o", start_open=True))
    y = H - TASKBAR_HEIGHT - 200
    assert closed.pixelColor(W // 2, y) != opened.pixelColor(W // 2, y)


def test_start_panel_is_opaque_enough_to_read(tmp_path):
    """The panel must not ghost the windows behind it: its interior is a flat surface."""
    image = QImage(shot(tmp_path, "start", start_open=True))
    y = H - TASKBAR_HEIGHT - 120          # inside the Start panel, below the pinned grid
    samples = [image.pixelColor(x, y).lightness() for x in range(W // 2 - 250, W // 2 + 250, 25)]
    assert max(samples) - min(samples) < 30, "Start background is not uniform (content bleeding through)"


def test_quick_settings_opens_on_the_right_above_the_taskbar(tmp_path):
    plain, quick = QImage(shot(tmp_path, "p")), QImage(shot(tmp_path, "q", quick_open=True))
    probe = (W - 180, H - TASKBAR_HEIGHT - 120)
    assert plain.pixelColor(*probe) != quick.pixelColor(*probe)
    # and the desktop far from the flyout is untouched
    assert plain.pixelColor(200, 600) == quick.pixelColor(200, 600)


def test_context_menu_renders_where_it_was_opened(tmp_path):
    plain, menu = QImage(shot(tmp_path, "p2")), QImage(shot(tmp_path, "m", context_open=True))
    assert plain.pixelColor(60, 60) != menu.pixelColor(60, 60)


def test_light_theme_is_actually_light(tmp_path):
    dark = QImage(shot(tmp_path, "d"))
    light = QImage(shot(tmp_path, "l", light=True))
    row = H - TASKBAR_HEIGHT // 2
    assert light.pixelColor(20, row).lightness() > dark.pixelColor(20, row).lightness() + 60


def test_english_locale_renders(tmp_path):
    assert QImage(shot(tmp_path, "en", locale="en")).width() == W


def test_a_bad_output_path_fails_loudly(tmp_path):
    with pytest.raises(Exception):
        render("/definitely/not/a/directory/out.png")


def test_taskbar_tray_really_draws_icons_not_empty_space(tmp_path):
    """The tray strip must contain drawn glyph pixels — the icon pipeline silently produced blank
    images once, and only a pixel check caught it."""
    image = QImage(shot(tmp_path, "tray"))
    row_top, row_bottom = H - TASKBAR_HEIGHT + 12, H - 12
    lit = sum(1 for x in range(W - 260, W - 130) for y in range(row_top, row_bottom)
              if image.pixelColor(x, y).lightness() > 120)
    assert lit > 40, f"tray icons look blank ({lit} lit pixels)"


def test_desktop_icons_come_from_the_icon_theme(tmp_path):
    """Desktop icons must be the real Win11 theme artwork: coloured, not a flat glyph square."""
    image = QImage(shot(tmp_path, "deskicons"))
    saturated = sum(1 for x in range(44, 92) for y in range(20, 68)
                    if image.pixelColor(x, y).saturation() > 80
                    and image.pixelColor(x, y).value() > 90)
    assert saturated > 120, f"the first desktop icon is not themed artwork ({saturated} px)"


def test_context_menu_is_opaque(tmp_path):
    """Text behind the menu must not read through it."""
    image = QImage(shot(tmp_path, "menuopaque", context_open=True))
    samples = [image.pixelColor(x, 240).lightness() for x in range(30, 230, 10)]
    assert max(samples) - min(samples) < 25, "content bleeding through the context menu"


def test_pinned_apps_show_real_coloured_icons(tmp_path):
    """Start pins must render the vendored colour icons, not only grey lettered squares."""
    image = QImage(shot(tmp_path, "pins", start_open=True))
    saturated = 0
    for x in range(520, 1060, 3):
        for y in range(348, 384, 3):
            c = image.pixelColor(x, y)
            if c.saturation() > 90 and c.value() > 90:
                saturated += 1
    assert saturated > 60, f"pinned icons look colourless ({saturated} saturated pixels)"


def test_wallpaper_is_drawn(tmp_path):
    """The desktop must show the wallpaper, not a flat fill: brightness varies across the surface."""
    image = QImage(shot(tmp_path, "wall"))
    samples = [image.pixelColor(x, 700).lightness() for x in range(20, 1580, 40)]
    assert max(samples) - min(samples) > 25, "desktop looks like a flat colour"
