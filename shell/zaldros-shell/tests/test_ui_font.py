"""Guard: the shipped UI font can actually draw the interface.

Regression (run #28c): the vendored family was Selawik — metrically Segoe UI, but a Latin-only
cmap with 383 glyphs and not one Cyrillic letter. The interface is Russian, so every label in the
shell was drawn by fontconfig's fallback (DejaVu Sans on our ISO): the shell claimed one font and
the screen showed another, which is exactly what the maintainer saw.

These tests fail if the shipped font stops covering the text we ship, if the family named by the
shell and by the system theme drift apart, or if the font is not installed system-wide (KWin,
Dolphin and Konsole read fontconfig, not our QML).
"""

import re
import sys
from pathlib import Path

import pytest
from PySide6.QtGui import QGuiApplication, QRawFont

REPO = Path(__file__).resolve().parents[3]
FONT_DIR = REPO / "assets" / "fonts" / "pt-sans"
THEME = REPO / "system" / "theme" / "install-visual-theme.sh"
APP = REPO / "shell" / "zaldros-shell" / "zaldros_shell" / "app.py"
UI_SOURCES = (REPO / "shell" / "zaldros-shell" / "qml", REPO / "shell" / "zaldros-shell" / "zaldros_shell")

FAMILY = "PT Sans"


@pytest.fixture(scope="module", autouse=True)
def _qt_app():
    """QRawFont needs a QGuiApplication; the same Qt that draws the shell answers the question."""
    yield QGuiApplication.instance() or QGuiApplication(sys.argv[:1])


def _supports(ttf: Path, characters) -> list[str]:
    """Characters the face cannot draw, asked of Qt itself rather than of a cmap parser."""
    face = QRawFont(str(ttf), 14)
    assert not face.familyName() == "", f"Qt cannot load {ttf.name}"
    return [c for c in characters if not face.supportsCharacter(ord(c))]


def _shipped_faces() -> list[Path]:
    return sorted(FONT_DIR.glob("*.ttf"))


def _ui_text() -> set[str]:
    """Every character the shell can put on screen from its own source."""
    characters: set[str] = set()
    for root in UI_SOURCES:
        for path in list(root.rglob("*.qml")) + list(root.rglob("*.py")):
            characters |= set(path.read_text(encoding="utf-8"))
    printable = {c for c in characters if c.isprintable() and not c.isspace()}
    return printable


def test_font_faces_are_vendored_with_their_licence() -> None:
    names = {path.name for path in _shipped_faces()}
    assert {"PTSans-Regular.ttf", "PTSans-Bold.ttf"} <= names, names
    assert (FONT_DIR / "LICENSE.txt").exists(), "OFL text must travel with the font"


def test_shipped_font_covers_cyrillic() -> None:
    """The specific failure: a UI font with no Cyrillic at all."""
    alphabet = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдеёжзийклмнопрстуфхцчшщъыьэюя"
    for face in _shipped_faces():
        missing = _supports(face, alphabet)
        assert not missing, f"{face.name} cannot draw: {''.join(missing)}"


def test_shipped_font_covers_every_character_the_ui_uses() -> None:
    """Not just the alphabet: whatever literal text lives in the shell sources."""
    for face in _shipped_faces():
        # Source-only punctuation that never reaches a label is not worth failing over, but any
        # letter or digit is.
        wanted = sorted(c for c in _ui_text() if c.isalnum())
        missing = _supports(face, wanted)
        assert not missing, f"{face.name} misses characters used in the UI: {missing}"


def test_shell_and_system_theme_name_the_same_family() -> None:
    assert f'UI_FONT_PREFERENCE = ("{FAMILY}",)' in APP.read_text(), "shell preference drifted"
    theme = THEME.read_text()
    assert f'UI_FONT_FAMILY="{FAMILY}"' in theme, "theme installer names another family"
    # No stale literal family names left behind in the config it writes.
    for line in theme.splitlines():
        if re.search(r"(gtk-font-name|font-name|^font=|activeFont|menuFont)", line):
            assert "Selawik" not in line, f"stale font name: {line.strip()}"


def test_font_is_installed_system_wide_not_only_in_the_shell() -> None:
    theme = THEME.read_text()
    assert "/usr/share/fonts/truetype/zaldros" in theme, "font must be installed for all apps"
    assert "60-zaldros-ui-font.conf" in theme, "fontconfig must map sans-serif to the UI font"
    assert "PT-Sans-OFL.txt" in theme, "licence must be installed into the image"
