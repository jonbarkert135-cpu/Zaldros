"""Windows 11 snap layouts: the six layouts, and what snapping does to a window.

The flyout's geometry is checked by tools/visual/parity.py (test_visual_parity). What is checked
here is the part a screenshot cannot show:

* the zone fractions in the QML are the ones measured from Microsoft's own capture
  (system/theme/win11-reference.json → snap_layouts.zones, re-derived by
  tools/visual/measure_library.py), and
* snapping a window really moves it into that fraction of the work area — every zone of every
  layout, through the same applySnap path the flyout uses.
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
SNAP = REFERENCE["snap_layouts"]
SCREEN = (1280, 800)
WORK = (SCREEN[0], SCREEN[1] - REFERENCE["taskbar"]["height"])


@pytest.fixture(scope="module")
def shell(qt_app):
    """One live shell scene; the tests drive it through the QML functions, without rendering."""
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


def _flyout(shell):
    from PySide6.QtCore import QObject
    flyout = shell.findChild(QObject, "snapFlyout")
    assert flyout is not None, "the shell has no snap layouts flyout"
    return flyout


def _call(shell, method, *args):
    from PySide6.QtCore import QMetaObject, Q_ARG
    QMetaObject.invokeMethod(shell, method, *[Q_ARG("QVariant", value) for value in args])


def test_the_six_layouts_are_the_measured_ones(shell):
    layouts = _flyout(shell).property("layouts").toVariant()
    assert len(layouts) == SNAP["layouts"]
    measured = [[[zone["x"], zone["y"], zone["w"], zone["h"]] for zone in layout]
                for layout in layouts]
    for index, (actual, expected) in enumerate(zip(measured, SNAP["zones"])):
        assert len(actual) == len(expected), f"layout {index + 1} has the wrong number of zones"
        for zone_actual, zone_expected in zip(actual, expected):
            for value_actual, value_expected in zip(zone_actual, zone_expected):
                assert abs(value_actual - value_expected) < 0.001, \
                    f"layout {index + 1} drifted from the measured reference"


def test_every_zone_covers_the_work_area(shell):
    """A layout's zones must tile the work area exactly: no overlap, no gap, no leftover."""
    layouts = _flyout(shell).property("layouts").toVariant()
    for index, layout in enumerate(layouts):
        area = sum(zone["w"] * zone["h"] for zone in layout)
        assert abs(area - 1.0) < 0.001, f"layout {index + 1} does not cover the screen"
        for zone in layout:
            assert zone["x"] + zone["w"] <= 1.001 and zone["y"] + zone["h"] <= 1.001


def test_snapping_moves_the_window_into_its_zone(shell):
    from PySide6.QtCore import QObject
    window = shell.findChild(QObject, "explorerWindow")
    layouts = _flyout(shell).property("layouts").toVariant()
    for layout_index, layout in enumerate(layouts):
        for zone in layout:
            _call(shell, "applySnap", "explorer", zone)
            expected = (round(zone["x"] * WORK[0]), round(zone["y"] * WORK[1]),
                        round(zone["w"] * WORK[0]), round(zone["h"] * WORK[1]))
            actual = (window.property("x"), window.property("y"),
                      window.property("width"), window.property("height"))
            assert actual == expected, \
                f"layout {layout_index + 1} zone {zone} put the window at {actual}"
    _call(shell, "clearSnap", "explorer")
    assert window.property("width") != round(layouts[0][0]["w"] * WORK[0]), \
        "clearing the snap must give the window its own size back"


def test_snapping_replaces_maximised_state(shell):
    from PySide6.QtCore import QObject
    window = shell.findChild(QObject, "explorerWindow")
    shell.setProperty("maximised", {"explorer": True})
    _call(shell, "applySnap", "explorer", {"x": 0.5, "y": 0, "w": 0.5, "h": 1})
    assert window.property("width") == WORK[0] / 2, "a snapped window must not stay maximised"
    assert shell.property("maximised").toVariant()["explorer"] is False
    _call(shell, "clearSnap", "explorer")


def test_the_flyout_opens_and_closes_like_every_other_flyout(shell):
    _call(shell, "openSnapMenu", "explorer", 600.0, 100.0)
    assert shell.property("snapOpen") is True
    assert shell.property("snapTarget") == "explorer"
    _call(shell, "closeAllFlyouts")
    assert shell.property("snapOpen") is False, "Esc and clicks elsewhere must close the flyout"


def test_win_z_and_the_maximise_button_are_wired():
    shell_source = (ROOT / "shell" / "zaldros-shell" / "qml" / "Shell.qml").read_text()
    window_source = (ROOT / "shell" / "zaldros-shell" / "qml" / "AppWindow.qml").read_text()
    assert '"Meta+Z"' in shell_source, "Win+Z must open the snap layouts"
    assert "snapMenuRequested" in window_source
    assert "onSnapMenuRequested" in shell_source
    # Windows opens the flyout on a rest, not on a click: the delay has to be there.
    assert "snapDelay" in window_source and "interval: 400" in window_source


def test_kwin_still_tiles_real_windows_with_meta_arrows():
    """Our own windows snap through the flyout; real applications need KWin's quick tiling."""
    installer = (ROOT / "system" / "theme" / "install-visual-theme.sh").read_text()
    for action in ("Window Quick Tile Left=Meta+Left",
                   "Window Quick Tile Right=Meta+Right",
                   "Window Maximize=Meta+Up",
                   "Window Minimize=Meta+Down"):
        assert action in installer, f"kglobalshortcutsrc no longer seeds {action}"
