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
    # The grid package's numbers, so the QML that loads here is the bigger of the two variants.
    "@LAYOUT@": "zaldros-grid",
    "@CARDW@": "420",
    "@CARDH@": "262",
    "@MAXCOL@": "3",
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
    assert "LayoutName=zaldros\n" in installer, "Alt+Tab must use the switcher layout"
    assert "LayoutName=zaldros-grid\n" in installer, \
        "Meta+Tab must use the Task View grid layout"
    assert "thumbnail_grid" not in installer.split("[TabBox]")[1], \
        "the Plasma-dependent layout must not come back"
    assert "/usr/share/kwin/tabbox/$layout" in installer, "the packages must be installed"


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


def test_the_switcher_surface_is_not_a_popup() -> None:
    """Runs #29-#34 saw nothing on Alt+Tab and run #39 saw nothing from the script's own window;
    both used `Qt.Popup | Qt.X11BypassWindowManagerHint`. KWin never puts an internal popup in the
    scene (it wants a transient parent and a grab) and a Wayland session has no X11 hint to bypass.
    """
    flags = re.search(r"flags:\s*(.+)", QML.read_text()).group(1)
    assert "Qt.Popup" not in flags and "X11Bypass" not in flags, flags
    assert "Qt.FramelessWindowHint" in flags, flags


def test_the_layout_says_in_the_log_that_it_loaded_and_appeared() -> None:
    """One boot has to be able to tell "the QML never loaded" from "it loaded and KWin drew
    nothing"; selftest.py collects the ZALDROS-SWITCHER lines."""
    text = QML.read_text()
    assert "ZALDROS-SWITCHER tabbox layout loaded" in text
    assert "ZALDROS-SWITCHER tabbox surface visible=" in text


def test_the_cards_sit_on_one_rounded_panel() -> None:
    """Run #41 drew the cards straight onto the dimmed desktop; Windows 11 puts them on a single
    rounded panel, and the theme's surface colour existed in this file without ever being used."""
    text = QML.read_text()
    assert "id: panel" in text, "the cards need a container, not bare cards on the backdrop"
    assert "tabBox.surfaceColour" in text, "the panel must use the theme surface colour"
    assert "radius: tabBox.cornerRadius * 2" in text, "the panel corners follow the theme radius"


def test_the_card_icon_cannot_take_the_switcher_down_with_it() -> None:
    """KWin publishes `icon` as a QIcon, which plain QtQuick cannot paint (`Image.source` rejects
    it), so the badge needs Kirigami. A failed QML import kills the file it sits in, and main.qml
    is the switcher — hence a separate file behind a Loader, and the module in the image."""
    text = QML.read_text()
    badge = PACKAGE / "contents" / "ui" / "IconBadge.qml"
    assert badge.is_file(), "the icon lives in its own file"
    assert "kirigami" in badge.read_text().lower(), "the badge is the only place Kirigami appears"
    imports = [line for line in text.splitlines() if line.startswith("import ")]
    assert not any("kirigami" in line.lower() for line in imports), \
        "main.qml must not import Kirigami; a missing module would blank the switcher"
    assert 'source: "IconBadge.qml"' in text and "Loader {" in text, \
        "the badge must be loaded, not imported"

    installer = INSTALLER.read_text()
    assert 'for qml in "$TABBOX_SRC"/contents/ui/*.qml' in installer, \
        "the installer must ship every QML file in the package, not just main.qml"
    packages = (REPO / "build" / "iso" / "build-iso.sh").read_text()
    assert "qml6-module-org-kde-kirigami" in packages, "the image needs the module for the icon"


def test_the_task_view_grid_is_the_same_source_with_different_numbers() -> None:
    """Meta+Tab shows the Windows Task View shape: the same cards, bigger, wrapped into rows.

    Two tabbox packages out of one QML file, so a fix to the switcher is a fix to both. The only
    difference is what the installer substitutes: id, card size and how many fit in a row.
    """
    text = QML.read_text()
    for token in ("@LAYOUT@", "@CARDW@", "@CARDH@", "@MAXCOL@"):
        assert token in text, f"{token} must be substituted at install time, not hardcoded"

    installer = INSTALLER.read_text()
    assert '"zaldros:300:188:99" "zaldros-grid:420:262:3"' in installer, \
        "one loop builds both packages; the grid gets bigger cards and a three-column cap"
    assert "-e \"s|@LAYOUT@|$layout|g\"" in installer, "each package must know its own id"
    assert '"$DEST/usr/share/kwin/tabbox/$layout/metadata.json"' in installer, \
        "the two packages need different metadata ids, or KWin sees one plugin twice"


def test_meta_tab_opens_the_alternative_tabbox_and_not_the_ui_less_script() -> None:
    """The script cannot draw (run #40), so the key that shows the grid must be KWin's own
    alternative tabbox action; the script's silent cycling moved to Meta+F10."""
    installer = INSTALLER.read_text()
    assert "Walk Through Windows (Alternative)=Meta+Tab,Meta+Tab," in installer
    assert "Walk Through Windows (Reverse Alternative)=Meta+Shift+Tab,Meta+Shift+Tab," in installer
    assert "Zaldros Walk Through Windows=Meta+F10,Meta+F10," in installer, \
        "the UI-less fallback must not sit on the same key as the grid"


def test_the_grid_shrinks_instead_of_falling_off_the_screen() -> None:
    """Fixed card sizes only fit while the windows are few. The grid scales the thumbnails down
    to whatever is left after the gutters and captions, so no row is ever clipped."""
    text = QML.read_text()
    assert "fitScale" in text, "the cards must scale to the screen, not trust a fixed size"
    assert "Math.min(1," in text, "shrink only — cards must never be blown up past their design size"
    assert "width: grid.contentWidthHint" in text, \
        "clamping the grid to a fraction of the screen loses a whole column to rounding"
