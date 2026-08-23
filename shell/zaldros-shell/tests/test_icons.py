"""The icon pipeline must produce real, correctly coloured pixels — a blank icon is a silent bug
that render tests alone would not catch (this is exactly how the first integration failed: QML sends
the colour URL-encoded, so `#ffffff` arrived as `%23ffffff` and every icon rendered empty).
"""
import os
import sys

import pytest

pytest.importorskip("PySide6")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSize  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402

from zaldros_shell.app import ASSETS  # noqa: E402
from zaldros_shell.icons import IconProvider  # noqa: E402

app = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])
provider = IconProvider(ASSETS / "icons" / "fluent")


def opaque_pixels(image):
    return [image.pixelColor(x, y) for x in range(image.width()) for y in range(image.height())
            if image.pixelColor(x, y).alpha() > 200]


def test_vendored_glyph_set_covers_every_glyph_the_shell_asks_for():
    qml = " ".join((ASSETS.parent / "shell" / "zaldros-shell" / "qml" / name).read_text()
                   for name in os.listdir(ASSETS.parent / "shell" / "zaldros-shell" / "qml")
                   if name.endswith(".qml"))
    import re
    used = {m for m in re.findall(r'glyph: "([a-z-]+)"', qml)}
    have = {p.stem for p in (ASSETS / "icons" / "fluent").glob("*.svg")}
    assert used <= have, f"missing vendored icons: {sorted(used - have)}"


def test_icon_is_rendered_in_the_requested_colour():
    image = provider.requestImage("wifi?%23ffffff", QSize(), QSize(32, 32))
    pixels = opaque_pixels(image)
    assert pixels, "icon rendered empty"
    assert all(p.red() > 240 and p.green() > 240 and p.blue() > 240 for p in pixels)


def test_the_same_icon_can_be_rendered_dark_for_the_light_theme():
    pixels = opaque_pixels(provider.requestImage("wifi?%23000000", QSize(), QSize(32, 32)))
    assert pixels and all(p.red() < 40 for p in pixels)


def test_unknown_glyph_returns_a_null_image_rather_than_a_wrong_icon():
    assert provider.requestImage("no-such-glyph", QSize(), QSize(32, 32)).isNull()


def test_unknown_application_icon_falls_back_instead_of_guessing():
    assert provider.requestImage("app/definitely-not-installed-app", QSize(), QSize(32, 32)).isNull()
