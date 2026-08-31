"""Windows 11 snap bar: drag a window to the top edge and the layouts drop down.

The bar's geometry is checked by tools/visual/parity.py (test_visual_parity) against
win11-reference.json → snap_bar. What is checked here is the behaviour a screenshot cannot show:
who opens the bar, when it closes, and that a click on one of its zones snaps the window that was
being dragged — not the focused one.
"""
import json
import os
import sys
from pathlib import Path

import pytest

pytest.importorskip("PySide6")

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shell" / "zaldros-shell"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

REFERENCE = json.loads((ROOT / "system" / "theme" / "win11-reference.json").read_text())
BAR = REFERENCE["snap_bar"]
SNAP = REFERENCE["snap_layouts"]
SCREEN = (1280, 800)
WORK = (SCREEN[0], SCREEN[1] - REFERENCE["taskbar"]["height"])
QML = ROOT / "shell" / "zaldros-shell" / "qml"


@pytest.fixture(scope="module")
def shell(qt_app):
    from PySide6.QtQuick import QQuickView
    from zaldros_shell import app

    view, backends = app.build_view(tick=False)
    app._KEEPALIVE.extend([view, *backends])
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    view.setWidth(SCREEN[0])
    view.setHeight(SCREEN[1])
    root = view.rootObject()
    root.setProperty("width", SCREEN[0])
    root.setProperty("height", SCREEN[1])
    return root


def _call(shell, method, *args):
    from PySide6.QtCore import QMetaObject, Q_ARG
    QMetaObject.invokeMethod(shell, method, *[Q_ARG("QVariant", value) for value in args])


def _bar(shell):
    from PySide6.QtCore import QObject
    bar = shell.findChild(QObject, "snapBar")
    assert bar is not None, "the shell has no snap bar"
    return bar


def test_the_bar_carries_the_same_strip_as_the_flyout(shell):
    """One measured layout set, two surfaces — the bar must not grow its own numbers."""
    from PySide6.QtCore import QObject
    strip = shell.findChild(QObject, "snapBarLayouts")
    flyout = shell.findChild(QObject, "snapFlyout")
    bar_layouts = strip.property("layouts").toVariant()
    flyout_layouts = flyout.property("layouts").toVariant()
    assert len(bar_layouts) == SNAP["layouts"]
    assert bar_layouts == flyout_layouts, "the bar and the flyout must offer the same layouts"


def test_the_bar_is_the_derived_size(shell):
    """panel_height = header band + thumbnail strip + bottom padding, all from the reference."""
    bar = _bar(shell)
    assert abs(bar.property("width") - BAR["panel_width"]) <= BAR["tolerance"]
    assert abs(bar.property("height") - BAR["panel_height"]) <= BAR["tolerance"]


def test_dragging_a_window_to_the_top_edge_opens_and_closes_the_bar(shell):
    assert shell.property("snapBarOpen") is False, "the bar must stay away until asked for"
    _call(shell, "requestSnapBar", "explorer", True)
    assert shell.property("snapBarOpen") is True
    assert shell.property("snapBarTarget") == "explorer"
    # A different window moving away from the edge must not steal the bar from the dragged one.
    _call(shell, "requestSnapBar", "settings", False)
    assert shell.property("snapBarOpen") is True
    _call(shell, "requestSnapBar", "explorer", False)
    assert shell.property("snapBarOpen") is False, "leaving the top edge must close the bar"


def test_the_bar_snaps_the_dragged_window_not_the_focused_one(shell):
    from PySide6.QtCore import QObject
    shell.setProperty("focusedWindow", "explorer")
    _call(shell, "requestSnapBar", "settings", True)
    zone = {"x": 0.5, "y": 0, "w": 0.5, "h": 1}
    _call(shell, "applySnap", shell.property("snapBarTarget"), zone)
    settings = shell.findChild(QObject, "settingsWindow")
    assert (settings.property("x"), settings.property("width")) == (WORK[0] / 2, WORK[0] / 2)
    assert shell.property("snapBarOpen") is False, "snapping must put the bar away"
    _call(shell, "clearSnap", "settings")


def test_escape_closes_the_bar(shell):
    _call(shell, "requestSnapBar", "explorer", True)
    _call(shell, "closeAllFlyouts")
    assert shell.property("snapBarOpen") is False


def test_every_window_reports_the_top_edge():
    """All five windows must be wired, or the bar would only work for some of them."""
    window_source = (QML / "AppWindow.qml").read_text()
    shell_source = (QML / "Shell.qml").read_text()
    assert "signal snapBarRequested(bool atTopEdge)" in window_source
    assert "Theme.snapBarTrigger" in window_source, "the top-edge threshold must be a theme token"
    assert "drag.active" in window_source, "the bar may only appear while the window is dragged"
    for window in ("explorer", "settings", "taskmanager", "terminal", "devicemanager"):
        assert f'requestSnapBar("{window}"' in shell_source, f"{window} does not report the edge"


def test_the_header_band_comes_from_the_reference():
    """The 34 px of header content sit above the flyout's own 13 px padding: 47 px in total."""
    theme = (QML / "ZaldrosTheme" / "Theme.qml").read_text()
    header = int(theme.split("snapBarHeader:")[1].split("\n")[0].strip())
    padding = int(theme.split("snapPadding:")[1].split("\n")[0].strip())
    assert header + padding == BAR["header_band"]
