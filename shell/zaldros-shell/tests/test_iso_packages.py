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
    """Run #27: Alt+Tab failed in all nine boot profiles.

    KWin never grabs Alt+Tab itself. It asks the global accelerator daemon, which is only a
    *recommend* of kwin-wayland and was therefore absent from an image built with
    --no-install-recommends. Three things have to be true at once, so all three are asserted.
    """
    build = BUILD.read_text()
    theme = THEME.read_text()
    assert "kglobalacceld" in build, "the ISO must install a global shortcut daemon"
    session = build.split("cat > \"$ROOT/usr/local/bin/zaldros-session\"")[1]
    session = session.split("exec kwin_wayland")[0]
    assert "kglobalacceld" in session, (
        "the daemon must also be started by the session, before kwin_wayland"
    )
    assert "[TabBox]" in theme, "kwinrc must configure the window switcher"
    assert "Walk Through Windows=Alt+Tab" in theme, (
        "kglobalshortcutsrc must bind Alt+Tab to the KWin window walker"
    )
