"""Windows 11 edge drag (Aero Snap): drop a window against a screen edge and it takes that zone.

Microsoft's own description (support.microsoft.com/en-us/windows/experience/snap-your-windows):
"Drag a window to the left or right edge of the screen and release it to snap it to that half of
the screen; drag it into a corner to snap it to a quadrant."

That is the part our snap layouts flyout did not cover: until now the zone was chosen by clicking
a layout cell, never by where the pointer let go. The geometry of the preview pane lives in
tools/visual/parity.py (states "edgedrag" and "edgedragcorner"); what is checked here is the
decision: which point means which zone, that leaving the edge means nothing, and that a drop
snaps the window that was dragged — not the focused one.
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
SCREEN = (1280, 800)
WORK = (SCREEN[0], SCREEN[1] - REFERENCE["taskbar"]["height"])

LEFT_HALF = {"x": 0.0, "y": 0.0, "w": 0.5, "h": 1.0}
RIGHT_HALF = {"x": 0.5, "y": 0.0, "w": 0.5, "h": 1.0}
TOP_LEFT = {"x": 0.0, "y": 0.0, "w": 0.5, "h": 0.5}
BOTTOM_RIGHT = {"x": 0.5, "y": 0.5, "w": 0.5, "h": 0.5}


@pytest.fixture()
def shell(qt_app):
    """A fresh shell per test: snap and drag state is global, so tests must not inherit it."""
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


def _zone_at(shell, x, y):
    from PySide6.QtCore import QMetaObject, Q_ARG, Q_RETURN_ARG
    from PySide6.QtQml import QJSValue
    value = QMetaObject.invokeMethod(shell, "edgeZoneAt", Q_RETURN_ARG("QVariant"),
                                     Q_ARG("QVariant", float(x)), Q_ARG("QVariant", float(y)))
    return value.toVariant() if isinstance(value, QJSValue) else value


def _snapped(shell):
    """The snapped map. A QML object property comes back as QJSValue and needs toVariant()."""
    from PySide6.QtQml import QJSValue
    value = shell.property("snapped")
    return value.toVariant() if isinstance(value, QJSValue) else value


def _preview(shell):
    from PySide6.QtCore import QObject
    item = shell.findChild(QObject, "edgePreview")
    assert item is not None, "the shell draws no edge preview pane"
    return item


def test_left_edge_means_the_left_half(shell):
    assert _zone_at(shell, 1, WORK[1] / 2) == LEFT_HALF


def test_right_edge_means_the_right_half(shell):
    assert _zone_at(shell, SCREEN[0] - 1, WORK[1] / 2) == RIGHT_HALF


def test_top_corner_means_a_quadrant(shell):
    assert _zone_at(shell, 1, 10) == TOP_LEFT


def test_bottom_right_corner_means_the_lower_right_quadrant(shell):
    assert _zone_at(shell, SCREEN[0] - 1, WORK[1] - 10) == BOTTOM_RIGHT


def test_the_middle_of_the_screen_means_no_snap(shell):
    assert _zone_at(shell, SCREEN[0] / 2, WORK[1] / 2) is None


def test_below_the_work_area_means_no_snap(shell):
    """The taskbar is not a snap edge: a pointer over it must not arm a zone."""
    assert _zone_at(shell, 1, SCREEN[1] - 2) is None


def test_the_preview_pane_appears_only_while_a_zone_is_armed(shell):
    preview = _preview(shell)
    assert preview.property("visible") is False
    _call(shell, "reportDragPoint", "explorer", 1.0, float(WORK[1] / 2))
    assert preview.property("visible") is True
    assert (preview.property("width"), preview.property("height")) == (SCREEN[0] / 2, WORK[1])
    # dragged back into the middle of the screen: nothing is armed any more
    _call(shell, "reportDragPoint", "explorer", float(SCREEN[0] / 2), float(WORK[1] / 2))
    assert preview.property("visible") is False


def test_dropping_at_the_edge_snaps_that_window(shell):
    _call(shell, "reportDragPoint", "settings", 1.0, float(WORK[1] / 2))
    _call(shell, "dropDrag", "settings")
    assert _snapped(shell)["settings"] == LEFT_HALF
    assert _preview(shell).property("visible") is False


def test_dropping_away_from_the_edge_changes_nothing(shell):
    _call(shell, "reportDragPoint", "settings", float(SCREEN[0] / 2), float(WORK[1] / 2))
    _call(shell, "dropDrag", "settings")
    assert _snapped(shell) == {}


def test_a_drop_from_another_window_does_not_steal_the_zone(shell):
    """The armed zone belongs to the window that reported it, not to whoever releases next."""
    _call(shell, "reportDragPoint", "settings", 1.0, float(WORK[1] / 2))
    _call(shell, "dropDrag", "explorer")
    assert _snapped(shell) == {}


def test_a_drop_offers_snap_assist_like_every_other_snap(shell):
    _call(shell, "reportDragPoint", "explorer", 1.0, float(WORK[1] / 2))
    _call(shell, "dropDrag", "explorer")
    assert shell.property("snapAssistOpen") is True
    assert shell.property("snapAssistSource") == "explorer"
