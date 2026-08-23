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
