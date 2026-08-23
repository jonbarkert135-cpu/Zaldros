"""Visual smoke/regression tests: the shell must actually render, not merely parse.

Skipped when PySide6 is unavailable so the rest of the suite still runs; CI installs PySide6 so the
render gate runs there (spec PART 5 §8).
"""
import os
import sys

import pytest

pytest.importorskip("PySide6")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QImage  # noqa: E402

from bedrock_shell.app import render  # noqa: E402


@pytest.fixture(scope="module")
def desktop(tmp_path_factory):
    out = str(tmp_path_factory.mktemp("shots") / "desktop.png")
    return render(out, start_open=False, width=1280, height=800)


def test_desktop_renders_at_the_requested_size(desktop):
    image = QImage(desktop)
    assert (image.width(), image.height()) == (1280, 800)


def test_taskbar_is_actually_drawn_at_the_bottom(desktop):
    """The bottom 48 px must differ from the wallpaper above it — i.e. a taskbar exists."""
    image = QImage(desktop)
    # Sample an empty stretch of the taskbar (far left), not an icon, and the wallpaper above it.
    taskbar_pixel = image.pixelColor(60, image.height() - 24)
    wallpaper_pixel = image.pixelColor(60, image.height() - 200)
    assert taskbar_pixel != wallpaper_pixel, "no taskbar band drawn at the bottom of the frame"
    # The taskbar is a dark translucent band over the wallpaper.
    assert taskbar_pixel.lightness() < 90


def test_start_menu_changes_the_frame(tmp_path):
    closed = render(str(tmp_path / "closed.png"), start_open=False)
    opened = render(str(tmp_path / "open.png"), start_open=True)
    a, b = QImage(closed), QImage(opened)
    centre_closed = a.pixelColor(640, 400)
    centre_open = b.pixelColor(640, 400)
    assert centre_closed != centre_open, "Start menu did not appear in the rendered frame"


def test_render_fails_loudly_on_a_bad_path(tmp_path):
    with pytest.raises(RuntimeError):
        render(str(tmp_path / "no-such-dir" / "x.png"))
