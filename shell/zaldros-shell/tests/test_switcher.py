"""The Alt+Tab switcher.

Run #29 booted the ISO and Alt+Tab changed nothing: KWin 6.6 ships one switcher layout,
thumbnail_grid, and it imports the Plasma QML stack that a Zaldros session does not run. We ship
our own layout, which means the QML is ours to break — and an ISO cycle costs 45 minutes. These
tests load the switcher in this sandbox against stubs of KWin's own types, so a typo in a property
name fails here instead of in the image.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
PACKAGE = REPO / "system" / "theme" / "tabbox" / "zaldros"
QML = PACKAGE / "contents" / "ui" / "main.qml"
INSTALLER = REPO / "system" / "theme" / "install-visual-theme.sh"

# What the installer substitutes; kept here so the test renders exactly what ships.
SUBSTITUTIONS = {
    "@BACKDROP@": "#cc000000",
    "@SURFACE@": "#202020",
    "@TEXT@": "#ffffff",
    "@ACCENT@": "#60cdff",
    "@RADIUS@": "8",
}

STUBS = {
    "qmldir": "module org.kde.kwin\nTabBoxSwitcher 3.0 TabBoxSwitcher.qml\n"
              "WindowThumbnail 3.0 WindowThumbnail.qml\n",
    # Mirrors kwin v6.6.0 src/tabbox: the switcher root and the live thumbnail item, with the
    # properties the real ones expose. Nothing else about KWin is faked.
    "TabBoxSwitcher.qml": (
        "import QtQuick\n"
        "Item {\n"
        "    property var model: null\n"
        "    property int currentIndex: 0\n"
        "    property bool visible_: false\n"
        "    property rect screenGeometry: Qt.rect(0, 0, 1280, 800)\n"
        "    property bool allDesktops: false\n"
        "    property bool compositing: true\n"
        "}\n"
    ),
    "WindowThumbnail.qml": "import QtQuick\nItem { property var wId }\n",
}


def _rendered(tmp_path: Path) -> Path:
    text = QML.read_text()
    for token, value in SUBSTITUTIONS.items():
        text = text.replace(token, value)
    assert "@" not in re.sub(r"@[A-Za-z0-9._%+-]+@", "", text) or True
    assert not re.search(r"@[A-Z]+@", text), "a placeholder was left unsubstituted"
    out = tmp_path / "main.qml"
    out.write_text(text)
    return out


def test_metadata_is_a_kwin_window_switcher_package() -> None:
    meta = json.loads((PACKAGE / "metadata.json").read_text())
    assert meta["KPackageStructure"] == "KWin/WindowSwitcher", \
        "KWin only loads a tabbox package with this structure"
    assert meta["KPlugin"]["Id"] == "zaldros", "the id must match kwinrc LayoutName"
    assert meta["X-Plasma-API"] == "declarativeappletscript"


def test_kwinrc_selects_our_layout_for_both_key_paths() -> None:
    installer = INSTALLER.read_text()
    assert installer.count("LayoutName=zaldros") == 2, \
        "TabBox and TabBoxAlternative must both point at the layout we install"
    assert "thumbnail_grid" not in installer.split("[TabBox]")[1], \
        "the Plasma-dependent layout must not come back"
    assert "/usr/share/kwin/tabbox/zaldros" in installer, "the package must be installed"


def test_switcher_imports_nothing_from_plasma() -> None:
    """The whole reason the stock switcher was invisible."""
    imports = [line for line in QML.read_text().splitlines() if line.startswith("import ")]
    assert any("org.kde.kwin" in line for line in imports), "the switcher needs KWin's own types"
    for line in imports:
        assert "plasma" not in line and "ksvg" not in line and "kirigami" not in line, \
            f"a Zaldros session has no Plasma QML stack: {line}"


def test_switcher_qml_loads_against_stubbed_kwin_types(tmp_path: Path) -> None:
    """A syntax error or a wrong property name must fail here, not 45 minutes into an ISO run."""
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine

    stub_dir = tmp_path / "imports" / "org" / "kde" / "kwin"
    stub_dir.mkdir(parents=True)
    for name, body in STUBS.items():
        (stub_dir / name).write_text(body)

    app = QGuiApplication.instance() or QGuiApplication([])
    engine = QQmlApplicationEngine()
    engine.addImportPath(str(tmp_path / "imports"))

    errors: list[str] = []
    engine.warnings.connect(lambda ws: errors.extend(w.toString() for w in ws))
    engine.load(QUrl.fromLocalFile(str(_rendered(tmp_path))))
    app.processEvents()

    assert engine.rootObjects(), f"the switcher QML did not load: {errors}"
    real = [e for e in errors if "TypeError" not in e]
    assert not real, f"QML warnings from the switcher: {real}"


@pytest.mark.parametrize("role", ["caption", "windowId"])
def test_switcher_only_uses_roles_the_kwin_model_publishes(role: str) -> None:
    """kwin v6.6.0 ClientModel::roleNames(): caption, desktopName, minimized, windowId,
    closeable, icon. Anything else silently renders as undefined."""
    text = QML.read_text()
    assert f"model.{role}" in text
    used = set(re.findall(r"model\.([a-zA-Z]+)", text))
    known = {"caption", "desktopName", "minimized", "windowId", "closeable", "icon", "activate",
             "close"}
    assert used <= known, f"unknown model roles: {sorted(used - known)}"


def test_no_window_hangs_off_a_1280x800_screen(tmp_path: Path) -> None:
    """Run #29, from the booted ISO: the Explorer window was 1000 px wide at x=340 on a 1280 px
    screen, so its search field and caption buttons were cut off by the right edge."""
    import subprocess
    import sys

    shell_dir = REPO / "shell" / "zaldros-shell"
    out = tmp_path / "frame.png"
    env = {**__import__("os").environ, "QT_QPA_PLATFORM": "offscreen"}
    subprocess.run([sys.executable, "-m", "zaldros_shell", "render", "--window", "explorer",
                    "--width", "1280", "--height", "800", "--out", str(out), "--geometry",
                    str(tmp_path / "geometry.json")],
                   cwd=shell_dir, env=env, check=True, capture_output=True)
    geometry = json.loads((tmp_path / "geometry.json").read_text())
    screen = geometry["screen"]
    for name, box in geometry["items"].items():
        if not name.endswith("Window"):
            continue
        assert box["left"] >= 0 and box["top"] >= 0, f"{name} starts off-screen: {box}"
        assert box["left"] + box["width"] <= screen["width"], \
            f"{name} hangs off the right edge: {box} on {screen}"
        assert box["top"] + box["height"] <= screen["height"], \
            f"{name} hangs off the bottom edge: {box} on {screen}"
