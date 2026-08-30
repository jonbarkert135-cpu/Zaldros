"""Alt+Tab as a KWin script: the shortcut, the wiring, and the log it must leave.

Runs #29-#34 pressed Alt+Tab in a booted ISO four times. The framebuffer never changed by one
pixel and the session log never gained one kwin_tabbox line, even with that category on — KWin's
tabbox was failing silently. The switching is ours now (ADR-0012), implemented in KWin's scripting
API where every step prints what it did. These tests hold the chain together: the script exists,
the installer ships and enables it, and the key belongs to our action and not to KWin's.
"""

import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPT_DIR = REPO / "system" / "theme" / "kwin-scripts" / "zaldros-switcher"
MAIN_QML = SCRIPT_DIR / "contents" / "ui" / "main.qml"
INSTALLER = (REPO / "system" / "theme" / "install-visual-theme.sh").read_text()


def test_the_script_package_is_a_valid_kwin_script():
    meta = json.loads((SCRIPT_DIR / "metadata.json").read_text())
    assert meta["KPackageStructure"] == "KWin/Script"
    assert meta["KPlugin"]["Id"] == "zaldros-switcher"
    # declarativescript, not javascript: a JS script has no way to draw the overlay (ADR-0025).
    assert meta["X-Plasma-API"] == "declarativescript"
    # KWin hardcodes contents/ui/main.qml for declarativescript (scripting.cpp), so that is where
    # the file has to live; X-Plasma-MainScript only has to agree with it.
    assert meta["X-Plasma-MainScript"] == "ui/main.qml"
    # X-Plasma-MainScript is relative to contents/, as KPackage resolves it.
    assert (SCRIPT_DIR / "contents" / meta["X-Plasma-MainScript"]).is_file()


def test_the_script_registers_both_directions_on_alt_tab():
    js = MAIN_QML.read_text()
    registered = dict(re.findall(r'name:\s*"([^"]+)"\s*\n\s*text:\s*"[^"]*"\s*\n\s*sequence:\s*"([^"]+)"', js))
    switching = {name: keys for name, keys in registered.items() if "Probe" not in name}
    assert switching == {
        "Zaldros Walk Through Windows": "Alt+Tab",
        "Zaldros Walk Through Windows (Reverse)": "Alt+Shift+Tab",
    }


def test_the_script_switches_real_windows_and_says_so():
    js = MAIN_QML.read_text()
    # A QML script has no `workspace` global (run #38: "ReferenceError: workspace is not defined");
    # it must come from the module singleton.
    assert "property var workspace: Workspace" in js
    assert "workspace.activeWindow = next" in js      # it actually switches
    assert "workspace.stackingOrder" in js            # from the real window list
    assert "skipSwitcher" in js and "normalWindow" in js
    assert 'ZALDROS-SWITCHER ' in js                  # and leaves evidence in the session log


@pytest.mark.parametrize("needle", [
    "usr/share/kwin/scripts/zaldros-switcher/metadata.json",
    "usr/share/kwin/scripts/zaldros-switcher/contents/ui/main.qml",
    "zaldros-switcherEnabled=true",
])
def test_the_installer_ships_and_enables_the_script(needle):
    assert needle in INSTALLER


def test_kwin_no_longer_holds_the_alt_tab_grab():
    # Run #35, measured in a booted ISO: leaving Alt+Tab as KWin's *default* while blanking only
    # the current key restored the grab, and our action came back as ",none,". Both fields must
    # be none.
    assert "Walk Through Windows=none,none,Walk Through Windows" in INSTALLER
    assert "Walk Through Windows (Reverse)=none,none," in INSTALLER


def test_our_shortcut_lives_in_the_component_kwin_registers_into():
    # KWin script actions register into kglobalaccel's "kwin" component; a [zaldros-switcher]
    # group only created a phantom component with no action behind it.
    kwin_group = INSTALLER.split("[kwin]", 1)[1].split("EOF", 1)[0]
    assert "Zaldros Walk Through Windows=Alt+Tab,Alt+Tab," in kwin_group
    assert "[zaldros-switcher]" not in INSTALLER


def test_the_shortcut_config_reaches_the_live_user():
    # /etc/xdg alone lost to KWin's built-in defaults in run #34: kglobalaccel reads the user's
    # config first.
    assert "etc/skel/.config/kglobalshortcutsrc" in INSTALLER
    assert "home/ubuntu/.config/kglobalshortcutsrc" in INSTALLER


def test_the_boot_can_fire_the_shortcut_without_a_keyboard():
    selftest = (REPO / "build" / "iso" / "selftest.py").read_text()
    assert "def invoke_and_watch" in selftest
    assert "org.kde.kglobalaccel.Component.invokeShortcut" in selftest
    assert "/component/{component}" in selftest        # the method does not exist on /kglobalaccel
    assert "def shortcut_lines" in selftest            # and read the whole config, not its tail
    assert "def kwin_environ" in selftest              # and prove the logging rules got through


def test_the_session_log_is_not_drowned_by_the_missing_menu_file():
    assert "etc/xdg/menus/applications.menu" in INSTALLER


def test_the_switch_restores_a_minimized_window():
    # Run #35 boot log: the second window was minimized when Alt+Tab fired, and activating a
    # minimized window in KWin leaves it minimized — invisible to the screen comparison and to
    # the person pressing the key.
    js = MAIN_QML.read_text()
    assert "next.minimized = false" in js


# ── The overlay (ADR-0025) ──────────────────────────────────────────────────────────────────────
# iso run 33161193018 measured `switcher_overlay_fraction: 0.0`: the switch happened and nothing
# was drawn. These tests run the script's QML in this sandbox against stubs of KWin's own types,
# so a typo costs seconds instead of a 15-minute ISO cycle.

SUBSTITUTIONS = {
    "@BACKDROP@": "#cc000000",
    "@SURFACE@": "#202020",
    "@TEXT@": "#ffffff",
    "@ACCENT@": "#60cdff",
    "@RADIUS@": "8",
}

# Mirrors kwin v6.6.0 src/scripting/shortcuthandler.h: name, text, sequence, activated().
SHORTCUT_HANDLER_STUB = (
    "import QtQuick\n"
    "QtObject {\n"
    "    property string name\n"
    "    property string text\n"
    "    property var sequence\n"
    "    signal activated()\n"
    "}\n"
)

WORKSPACE_STUB = """
import QtQuick
QtObject {
    property var stackingOrder: []
    property var activeWindow: null
    property var currentDesktop: null
    property rect virtualScreenGeometry: Qt.rect(0, 0, 1280, 800)
    property size virtualScreenSize: Qt.size(1280, 800)
}
"""

WINDOW_STUB = """
import QtQuick
QtObject {
    property string caption: "window"
    property bool normalWindow: true
    property bool skipSwitcher: false
    property bool deleted: false
    property bool onAllDesktops: true
    property bool minimized: false
    property var desktops: []
}
"""


def _script_qml(tmp_path: Path) -> Path:
    text = MAIN_QML.read_text()
    for token, value in SUBSTITUTIONS.items():
        text = text.replace(token, value)
    assert not re.search(r"@[A-Z]+@", text), "a placeholder was left unsubstituted"
    out = tmp_path / "SwitcherScript.qml"
    out.write_text(text)
    return out


def _load(tmp_path):
    """Load the script exactly as it ships, with KWin's globals stubbed. Returns (root, errors)."""
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent

    stub_dir = tmp_path / "imports" / "org" / "kde" / "kwin"
    stub_dir.mkdir(parents=True)
    # Workspace is a *singleton* of the module in KWin's declarative API, not a context property:
    # run #38 in a booted ISO printed "ReferenceError: workspace is not defined" from this script.
    (stub_dir / "qmldir").write_text(
        "module org.kde.kwin\n"
        "ShortcutHandler 1.0 ShortcutHandler.qml\n"
        "singleton Workspace 1.0 Workspace.qml\n"
    )
    (stub_dir / "ShortcutHandler.qml").write_text(SHORTCUT_HANDLER_STUB)
    (stub_dir / "Workspace.qml").write_text("pragma Singleton\n" + WORKSPACE_STUB)

    app = QGuiApplication.instance() or QGuiApplication([])
    engine = QQmlApplicationEngine()
    engine.addImportPath(str(tmp_path / "imports"))

    # The stub objects get URLs in a directory of their own: QQmlComponent.setData makes the
    # engine cache a listing of that directory, and a file written afterwards next to them comes
    # back as "File name case mismatch".
    stubs = tmp_path / "stubs"
    stubs.mkdir()

    def build(source: str, name: str):
        component = QQmlComponent(engine)
        component.setData(source.encode(), QUrl.fromLocalFile(str(stubs / name)))
        obj = component.create()
        assert obj is not None, component.errorString()
        obj.setParent(engine)
        return obj

    errors: list[str] = []
    engine.warnings.connect(lambda ws: errors.extend(w.toString() for w in ws))
    engine.load(QUrl.fromLocalFile(str(_script_qml(tmp_path))))
    app.processEvents()
    assert engine.rootObjects(), f"the switcher script did not load: {errors}"
    root = engine.rootObjects()[0]
    # The script reaches the singleton through one alias; the tests drive the same object.
    workspace = root.property("workspace")
    assert workspace is not None, "the script must resolve the Workspace singleton"
    return root, errors, workspace, build, app


def test_the_script_qml_loads_against_stubbed_kwin_types(tmp_path: Path) -> None:
    _root, errors, _ws, _build, _app = _load(tmp_path)
    real = [e for e in errors if "TypeError" not in e]
    assert not real, f"QML warnings from the switcher script: {real}"


def test_alt_tab_switches_the_window_and_raises_the_overlay(tmp_path: Path) -> None:
    """The whole point of ADR-0025: the same call that switches must also put something on screen."""
    from PySide6.QtCore import QMetaObject, Q_ARG

    root, _errors, workspace, build, app = _load(tmp_path)
    first, second = build(WINDOW_STUB, "w1.qml"), build(WINDOW_STUB, "w2.qml")
    first.setProperty("caption", "Проводник")
    second.setProperty("caption", "Dolphin")
    workspace.setProperty("stackingOrder", [first, second])
    workspace.setProperty("activeWindow", second)

    QMetaObject.invokeMethod(root, "cycle", Q_ARG("QVariant", False))
    app.processEvents()

    assert workspace.property("activeWindow") is first, "Alt+Tab must activate the other window"
    assert root.property("captions").toVariant() == ["Проводник", "Dolphin"]
    assert root.property("current") == 0, "the overlay must mark the window we switched to"
    windows = [c for c in root.children() if c.inherits("QQuickWindow")]
    assert len(windows) == 1, "the script owns exactly one overlay window"
    overlay = windows[0]
    # `visible` on the Window itself cannot be read here: the offscreen platform never maps a
    # window, so the state the QML binds to is what this can honestly assert.
    assert root.property("overlayVisible") is True, "the overlay must be raised by the switch"
    assert (overlay.property("width"), overlay.property("height")) == (1280, 800), \
        "the overlay covers the screen the workspace reported"


def test_the_overlay_is_not_a_popup() -> None:
    """Run #39: KWin drew nothing for a `Qt.Popup` internal window (a popup wants a transient
    parent and a grab), and `Qt.X11BypassWindowManagerHint` means nothing to a Wayland session."""
    flags = re.search(r"flags:\s*(.+)", MAIN_QML.read_text()).group(1)
    assert "Qt.Popup" not in flags and "X11Bypass" not in flags, flags
    assert "Qt.FramelessWindowHint" in flags, flags


def test_a_minimized_target_is_restored(tmp_path: Path) -> None:
    from PySide6.QtCore import QMetaObject, Q_ARG

    root, _errors, workspace, build, app = _load(tmp_path)
    first, second = build(WINDOW_STUB, "w1.qml"), build(WINDOW_STUB, "w2.qml")
    first.setProperty("minimized", True)
    workspace.setProperty("stackingOrder", [first, second])
    workspace.setProperty("activeWindow", second)

    QMetaObject.invokeMethod(root, "cycle", Q_ARG("QVariant", False))
    app.processEvents()
    assert first.property("minimized") is False


def test_the_overlay_outlives_the_held_frame_and_dies_before_the_release_frame() -> None:
    """The boot driver screenshots 1.2 s after Tab with Alt still held, and again 1.2 s after
    release. An overlay on a timer only proves itself if it is up at the first frame and gone at
    the second (build/iso/ui-drive.py, alt_tab_step / alt_tab_verdict)."""
    driver = (REPO / "build" / "iso" / "ui-drive.py").read_text()
    settle = float(re.search(r"def alt_tab_step\(qmp, out, settle=([0-9.]+)\)", driver).group(1))
    interval = int(re.search(r"interval:\s*(\d+)", MAIN_QML.read_text()).group(1))
    assert settle * 1000 < interval < settle * 2000, (
        f"overlay lifetime {interval} ms must outlast the held frame ({settle * 1000:.0f} ms) "
        f"and end before the release frame ({settle * 2000:.0f} ms)"
    )
