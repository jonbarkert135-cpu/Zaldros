"""Keyboard and hit-box guards.

Run #25 booted PASS on all nine variant x profile combinations, and every host-injected keystroke
still left the framebuffer byte-identical: KWin runs bare here, so nothing but the shell itself can
answer Meta or Alt+Tab. These tests press the real keys on a real QQuickView and check the shell
state changed, and they check the shell publishes the Start button position the host driver clicks.
"""
import os
import sys

import pytest

pytest.importorskip("PySide6")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

from zaldros_shell.app import build_view, hit_boxes  # noqa: E402


@pytest.fixture(scope="module")
def view():
    app = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])
    view, backends = build_view(tick=False)
    view.resize(1280, 800)
    view.rootObject().setProperty("width", 1280)
    view.rootObject().setProperty("height", 800)
    view.show()
    QTest.qWaitForWindowExposed(view)
    yield view
    view.hide()
    del backends
    del app


def press(view, key, modifier=Qt.NoModifier):
    QTest.keyClick(view, key, modifier, 20)
    QTest.qWait(60)


def test_meta_toggles_start(view):
    root = view.rootObject()
    root.setProperty("startOpen", False)
    press(view, Qt.Key_Super_L)
    assert root.property("startOpen") is True, "Meta did not open Start"
    press(view, Qt.Key_Super_L)
    assert root.property("startOpen") is False, "Meta did not close Start"


def test_escape_closes_start(view):
    root = view.rootObject()
    root.setProperty("startOpen", True)
    press(view, Qt.Key_Escape)
    assert root.property("startOpen") is False


def test_alt_tab_switches_the_focused_window(view):
    root = view.rootObject()
    before = root.property("focusedWindow")
    press(view, Qt.Key_Tab, Qt.AltModifier)
    after = root.property("focusedWindow")
    assert after != before, "Alt+Tab did not move the focus between windows"
    press(view, Qt.Key_Tab, Qt.AltModifier)
    assert root.property("focusedWindow") == before


def test_start_button_hit_box_is_published_and_on_the_taskbar(view):
    boxes = hit_boxes(view)
    assert "startButton" in boxes, "the host UI driver has no click target without this"
    box = boxes["startButton"]
    assert box["width"] > 0 and box["height"] > 0
    assert 0 < box["x"] < 1280
    # The taskbar is the bottom 48 px band; the Start button centre must sit inside it.
    assert 800 - 48 < box["y"] < 800
