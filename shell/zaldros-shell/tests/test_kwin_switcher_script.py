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
MAIN_JS = SCRIPT_DIR / "contents" / "code" / "main.js"
INSTALLER = (REPO / "system" / "theme" / "install-visual-theme.sh").read_text()


def test_the_script_package_is_a_valid_kwin_script():
    meta = json.loads((SCRIPT_DIR / "metadata.json").read_text())
    assert meta["KPackageStructure"] == "KWin/Script"
    assert meta["KPlugin"]["Id"] == "zaldros-switcher"
    assert meta["X-Plasma-API"] == "javascript"
    assert meta["X-Plasma-MainScript"] == "code/main.js"
    # X-Plasma-MainScript is relative to contents/, as KPackage resolves it.
    assert (SCRIPT_DIR / "contents" / meta["X-Plasma-MainScript"]).is_file()


def test_the_script_registers_both_directions_on_alt_tab():
    js = MAIN_JS.read_text()
    registered = dict(re.findall(r'registerShortcut\("([^"]+)",\s*"[^"]*",\s*"([^"]+)"', js))
    switching = {name: keys for name, keys in registered.items() if "Probe" not in name}
    assert switching == {
        "Zaldros Walk Through Windows": "Alt+Tab",
        "Zaldros Walk Through Windows (Reverse)": "Alt+Shift+Tab",
    }


def test_the_script_switches_real_windows_and_says_so():
    js = MAIN_JS.read_text()
    assert "workspace.activeWindow = next" in js      # it actually switches
    assert "workspace.stackingOrder" in js            # from the real window list
    assert "skipSwitcher" in js and "normalWindow" in js
    assert 'var LOG = "ZALDROS-SWITCHER "' in js      # and leaves evidence in the session log


@pytest.mark.parametrize("needle", [
    "usr/share/kwin/scripts/zaldros-switcher/metadata.json",
    "usr/share/kwin/scripts/zaldros-switcher/contents/code/main.js",
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
    js = MAIN_JS.read_text()
    assert "next.minimized = false" in js
