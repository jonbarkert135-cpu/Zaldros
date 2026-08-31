"""Windows 11 Snap Assist: after one window takes a zone, the free part offers the others.

Microsoft's own description of the feature (support.microsoft.com/en-us/windows/experience/
snap-your-windows): "When you snap a window to one side of the screen, Snap Assist will display
thumbnails of your other open windows, allowing you to quickly choose which window to snap to the
other side."

Geometry lives in tools/visual/parity.py (state "snapassist"). What is checked here is the
behaviour: which windows are offered, which zone they land in, and that Snap Assist does not ask
again for a window it just placed.
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
QML = ROOT / "shell" / "zaldros-shell" / "qml"

LEFT_HALF = {"x": 0.0, "y": 0.0, "w": 0.5, "h": 1.0}
TOP_LEFT_QUARTER = {"x": 0.0, "y": 0.0, "w": 0.5, "h": 0.5}
LEFT_THIRD = {"x": 0.0, "y": 0.0, "w": 1 / 3, "h": 1.0}


@pytest.fixture()
def shell(qt_app):
    """A fresh shell per test: Snap Assist state is global, so tests must not inherit it."""
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


def _returning(shell, method, *args):
    """A QML function's return value. Objects come back as QJSValue and need toVariant()."""
    from PySide6.QtCore import QMetaObject, Q_ARG, Q_RETURN_ARG
    from PySide6.QtQml import QJSValue
    value = QMetaObject.invokeMethod(shell, method, Q_RETURN_ARG("QVariant"),
                                     *[Q_ARG("QVariant", item) for item in args])
    return value.toVariant() if isinstance(value, QJSValue) else value


def _assist(shell):
    from PySide6.QtCore import QObject
    item = shell.findChild(QObject, "snapAssist")
    assert item is not None, "the shell has no Snap Assist"
    return item


def test_snapping_one_window_offers_the_others(shell):
    _call(shell, "applySnap", "explorer", LEFT_HALF)
    assert shell.property("snapAssistOpen") is True, "Snap Assist must follow a snap"
    assert shell.property("snapAssistSource") == "explorer"
    offered = [entry["id"] for entry in _assist(shell).property("candidates").toVariant()]
    # Explorer took the zone and is not offered again; Settings is the other open window.
    assert offered == ["settings"], offered


def test_it_covers_exactly_the_free_zone(shell):
    _call(shell, "applySnap", "explorer", LEFT_HALF)
    assist = _assist(shell)
    assert (assist.property("x"), assist.property("y")) == (WORK[0] / 2, 0)
    assert (assist.property("width"), assist.property("height")) == (WORK[0] / 2, WORK[1])


def test_choosing_a_window_snaps_it_into_that_zone_and_stops_asking(shell):
    from PySide6.QtCore import QObject
    _call(shell, "applySnap", "explorer", LEFT_HALF)
    _call(shell, "snapInto", "settings", shell.property("snapAssistZone"))
    settings = shell.findChild(QObject, "settingsWindow")
    assert (settings.property("x"), settings.property("width")) == (WORK[0] / 2, WORK[0] / 2)
    assert shell.property("snapAssistOpen") is False, "the second window must not re-open it"


def test_a_quadrant_leaves_the_opposite_half_free(shell):
    """The largest free rectangle next to a quarter is the full-height half beside it."""
    free = _returning(shell, "freeZone", TOP_LEFT_QUARTER)
    assert free == {"x": 0.5, "y": 0.0, "w": 0.5, "h": 1.0}


def test_a_third_leaves_the_remaining_two_thirds(shell):
    free = _returning(shell, "freeZone", LEFT_THIRD)
    assert free["x"] == pytest.approx(1 / 3)
    assert free["w"] == pytest.approx(2 / 3)
    assert (free["y"], free["h"]) == (0.0, 1.0)


def test_a_maximised_zone_leaves_nothing_and_shows_no_assist(shell):
    assert _returning(shell, "freeZone", {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0}) is None
    _call(shell, "applySnap", "explorer", {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0})
    assert shell.property("snapAssistOpen") is False


def test_a_window_already_holding_a_zone_is_not_offered(shell):
    _call(shell, "snapInto", "settings", {"x": 0.5, "y": 0.0, "w": 0.5, "h": 1.0})
    _call(shell, "applySnap", "explorer", LEFT_HALF)
    # Settings is snapped into the other half already, so nothing is left to offer.
    assert shell.property("snapAssistOpen") is False


def test_escape_dismisses_it(shell):
    _call(shell, "applySnap", "explorer", LEFT_HALF)
    _call(shell, "closeAllFlyouts")
    assert shell.property("snapAssistOpen") is False


def test_names_and_icons_come_from_one_source(shell):
    """The taskbar button and the Snap Assist card must never disagree about a window."""
    shell_source = (QML / "Shell.qml").read_text()
    assert 'name: shell.windowName("explorer")' in shell_source, \
        "the taskbar must read the shared window metadata, not its own literals"
    assert _returning(shell, "windowName", "taskmanager") == "Диспетчер задач"
    assert _returning(shell, "windowGlyph", "terminal") == "terminal"


def test_the_grid_keeps_the_screen_aspect(shell):
    """A card's preview stands for a screen, so it stays 16:9 instead of filling a tall strip."""
    from zaldros_shell import app
    _call(shell, "applySnap", "explorer", LEFT_HALF)
    # Repeater-created items have no QObject parent, so findChild cannot see them.
    preview = app._named_items(_assist(shell), {}).get("snapAssistPreview0")
    assert preview is not None, "no card preview was built"
    aspect = preview.property("width") / preview.property("height")
    assert abs(aspect - 16 / 9) < 0.05, aspect
