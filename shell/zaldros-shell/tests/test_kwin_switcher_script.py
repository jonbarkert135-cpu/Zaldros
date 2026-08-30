"""The KWin script: the Meta+Tab fallback, the probes, and the log it must leave.

History, all measured in booted ISOs: runs #29-#34 found Alt+Tab dead, so the switching moved into
a KWin script (ADR-0012). The script does switch — run #40 reported `switched: true`,
`switched_fraction: 0.475` — but it can never draw: its own diagnostic printed
`overlay window visible=false geometry=0,0 1280x800`, i.e. Qt refused to create the window at all,
because a KWin script may not own one.

So since run #40 Alt+Tab belongs to KWin's own action again and the visible switcher is KWin's
tabbox with our layout (tests/test_switcher.py). This script stays as the no-UI fallback on
Meta+Tab plus the diagnostic probes; these tests hold that wiring together.
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
    # declarativescript, not javascript: it needs the Workspace singleton and ShortcutHandler.
    assert meta["X-Plasma-API"] == "declarativescript"
    # KWin hardcodes contents/ui/main.qml for declarativescript (scripting.cpp), so that is where
    # the file has to live; X-Plasma-MainScript only has to agree with it.
    assert meta["X-Plasma-MainScript"] == "ui/main.qml"
    # X-Plasma-MainScript is relative to contents/, as KPackage resolves it.
    assert (SCRIPT_DIR / "contents" / meta["X-Plasma-MainScript"]).is_file()


def test_the_script_keeps_both_directions_on_the_fallback_key():
    js = MAIN_QML.read_text()
    registered = dict(re.findall(r'name:\s*"([^"]+)"\s*\n\s*text:\s*"[^"]*"\s*\n\s*sequence:\s*"([^"]+)"', js))
    switching = {name: keys for name, keys in registered.items() if "Probe" not in name}
    # Not Alt+Tab: that key is KWin's again, so the tabbox is what appears on it (run #40).
    assert switching == {
        "Zaldros Walk Through Windows": "Meta+Tab",
        "Zaldros Walk Through Windows (Reverse)": "Meta+Shift+Tab",
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


def test_kwin_holds_the_alt_tab_grab_again():
    # Run #40: only KWin itself can put a switcher on screen, so its own action keeps the key and
    # our layout rides inside its tabbox. Both fields are seeded — run #35 measured that a blank
    # current-key field alone is silently refilled from the default.
    assert "Walk Through Windows=Alt+Tab,Alt+Tab,Walk Through Windows" in INSTALLER
    assert "Walk Through Windows (Reverse)=Alt+Shift+Tab,Alt+Shift+Tab," in INSTALLER


def test_our_shortcut_lives_in_the_component_kwin_registers_into():
    # KWin script actions register into kglobalaccel's "kwin" component; a [zaldros-switcher]
    # group only created a phantom component with no action behind it.
    kwin_group = INSTALLER.split("[kwin]", 1)[1].split("EOF", 1)[0]
    assert "Zaldros Walk Through Windows=Meta+Tab,Meta+Tab," in kwin_group
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


# ── Behaviour, against stubs of KWin's own types ────────────────────────────────────────────────
# The script's QML runs in this sandbox against stubs, so a typo costs seconds instead of a
# 15-minute ISO cycle.

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


def test_the_fallback_switches_the_window(tmp_path: Path) -> None:
    """No UI is expected here any more — only that the right window becomes active."""
    from PySide6.QtCore import QMetaObject, Q_ARG

    root, _errors, workspace, build, app = _load(tmp_path)
    first, second = build(WINDOW_STUB, "w1.qml"), build(WINDOW_STUB, "w2.qml")
    first.setProperty("caption", "Проводник")
    second.setProperty("caption", "Dolphin")
    workspace.setProperty("stackingOrder", [first, second])
    workspace.setProperty("activeWindow", second)

    QMetaObject.invokeMethod(root, "cycle", Q_ARG("QVariant", False))
    app.processEvents()

    assert workspace.property("activeWindow") is first, "the fallback must activate the other window"


def test_the_script_owns_no_window() -> None:
    """Run #40, in a booted ISO: `overlay window visible=false geometry=0,0 1280x800`. Qt would not
    create a window for a KWin script whatever the flags were, so keeping one here would only be
    dead code that reads like a working overlay."""
    text = MAIN_QML.read_text()
    assert "Window {" not in text, "a KWin script cannot own a window (run #40)"
    assert "QtQuick.Window" not in text


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
