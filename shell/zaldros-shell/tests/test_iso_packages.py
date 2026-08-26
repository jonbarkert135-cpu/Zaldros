"""Guard: every PySide6 submodule imported by the shell must ship in the ISO.

Regression: the ISO shipped only python3-pyside6.qtquick, so `from PySide6.QtSvg
import QSvgRenderer` raised ModuleNotFoundError inside the live session and the
Zaldros shell never started (CI run 32674190956, commit e0636cf).
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PKG = REPO / "shell" / "zaldros-shell" / "zaldros_shell"
BUILD = REPO / "build" / "iso" / "build-iso.sh"

# Submodules provided by the base python3-pyside6.qtquick dependency chain.
BUNDLED = {"QtCore", "QtGui", "QtQml", "QtQuick", "QtNetwork"}


def _imported_submodules() -> set[str]:
    found = set()
    for path in PKG.rglob("*.py"):
        for m in re.finditer(r"from PySide6\.(\w+) import", path.read_text()):
            found.add(m.group(1))
    return found


def test_pyside6_submodules_have_iso_packages() -> None:
    base = BUILD.read_text()
    missing = [
        mod
        for mod in sorted(_imported_submodules() - BUNDLED)
        if f"python3-pyside6.{mod.lower()}" not in base
    ]
    assert not missing, f"missing ISO packages for PySide6 modules: {missing}"


THEME = REPO / "system" / "theme" / "install-visual-theme.sh"


def test_alt_tab_is_wired_end_to_end() -> None:
    """Run #27 blamed a missing global accelerator daemon; run #33 proved that diagnosis wrong.

    kwin v6.6.0 embeds the daemon: src/main_wayland.cpp does Q_IMPORT_PLUGIN(KGlobalAccelImpl)
    and src/globalshortcuts.cpp builds a KGlobalAccelD in-process, so kwin_wayland owns
    org.kde.kglobalaccel. A second kglobalacceld next to it exits 0 at once because the bus name
    is taken — run #33 logged exactly that, five times. The session must not spawn one.
    """
    build = BUILD.read_text()
    theme = THEME.read_text()
    session = build.split('/usr/local/bin/zaldros-session" <<\'EOS\'')[1].split("\nEOS")[0]
    assert "kglobalacceld exited" not in session, (
        "kwin_wayland is the accelerator daemon; starting a second one is a no-op loop"
    )
    assert "[TabBox]" in theme, "kwinrc must configure the window switcher"
    assert "Walk Through Windows=Alt+Tab" in theme, (
        "kglobalshortcutsrc must bind Alt+Tab to the KWin window walker"
    )


def test_the_image_can_interrogate_its_own_shortcut_daemon() -> None:
    """Run #30 failed Alt+Tab again with no way to tell which link in the chain broke. The image
    now carries gdbus so the self-test can ask kglobalaccel what KWin actually registered."""
    build = BUILD.read_text()
    assert "libglib2.0-bin" in build, "the self-test's D-Bus probe needs gdbus in the image"
    selftest = (REPO / "build" / "iso" / "selftest.py").read_text()
    assert "/usr/share/kwin/tabbox/zaldros" in selftest, (
        "the self-test must report whether our switcher package reached the image"
    )
    assert "Walk Through Windows" in selftest, (
        "the self-test must report whether the daemon knows KWin's own shortcut"
    )


def test_dbus_probes_run_inside_the_session_not_as_root() -> None:
    """Run #31's probe answered "component absent" only because systemd runs the self-test as
    root, and root has no session bus: the question was never delivered. Every D-Bus probe must
    go through the session user with DBUS_SESSION_BUS_ADDRESS set."""
    selftest = (REPO / "build" / "iso" / "selftest.py").read_text()
    assert "def user_sh(" in selftest, "the self-test needs a session-user command runner"
    assert "DBUS_SESSION_BUS_ADDRESS" in selftest.split("def user_sh(")[1].split("def ")[0], (
        "the runner must point at the session bus"
    )
    probe = selftest.split("def switcher(")[1].split("\ndef ")[0]
    assert not re.search(r'(?<!user_)sh\("gdbus"', probe), (
        "root gdbus calls answer nothing; use user_sh"
    )
    for fact in ("accel_running", "session_bus_socket", "dbus_kde_names"):
        assert fact in probe, f"the switcher probe must report {fact}"


def test_the_boot_records_what_kwin_says_about_the_switcher() -> None:
    """The session still waits for the user bus (kwin registers its services on it), and the boot
    now ends with a late report: KWin logs the switcher failure *while* Alt+Tab is pressed, which
    is 100 seconds after the boot self-test has already printed its JSON."""
    build = BUILD.read_text()
    session = build.split('/usr/local/bin/zaldros-session" <<\'EOS\'')[1].split("\nEOS")[0]
    assert "/bus" in session and "while [ ! -S" in session, (
        "the session must wait for the D-Bus socket before starting the compositor"
    )
    assert "kwin_tabbox.debug=true" in session, (
        "without the tabbox logging category a failed switcher load is silent"
    )
    assert "--late" in build, "the boot must dump the session log after the host drives Alt+Tab"
    selftest = (REPO / "build" / "iso" / "selftest.py").read_text()
    assert "def late_report(" in selftest and "tabbox_lines" in selftest, (
        "the late report must carry KWin's own tabbox messages"
    )


def test_the_switcher_qml_modules_are_in_the_image() -> None:
    """Our tabbox layout imports QtQuick.Window. A missing QML module is one warning in KWin's
    log and an Alt+Tab that draws nothing."""
    build = BUILD.read_text()
    qml = (REPO / "system" / "theme" / "tabbox" / "zaldros" / "contents" / "ui" / "main.qml").read_text()
    for line in qml.splitlines():
        if line.startswith("import QtQuick.Window"):
            assert "qml6-module-qtquick-window" in build, (
                "the layout imports QtQuick.Window, so the image must ship that QML module"
            )


def test_the_switcher_package_is_installed_by_the_theme_installer() -> None:
    theme = THEME.read_text()
    assert "/usr/share/kwin/tabbox/zaldros" in theme, "the layout must be installed where KWin looks"
    assert "LayoutName=zaldros" in theme, "and selected in kwinrc"


def test_the_image_configures_a_keyboard_it_can_actually_switch() -> None:
    """Run #30 booted with no keymap at all — localectl answered "(unset)". A Russian desktop ships
    two layouts and a way to swap them, and KWin reads that from kxkbrc, not kwinrc."""
    theme = THEME.read_text()
    assert "/etc/xdg/kxkbrc" in theme, "KWin reads layouts from kxkbrc (kwin v6.6.0 src/main.cpp)"
    kxkb = theme.split('"$DEST/etc/xdg/kxkbrc"')[1].split("EOF")[1]
    assert "LayoutList=us,ru" in kxkb and "grp:alt_shift_toggle" in kxkb
    assert "/etc/default/keyboard" in theme, "the console and X11 need the same keymap"
