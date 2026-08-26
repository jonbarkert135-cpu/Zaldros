"""Guard: the borrowed Plasma-store assets stay wired, licensed and inside our architecture.

Run #29 audited two "windows-eleven" Plasma global themes (docs/PLASMA_THEME_AUDIT.md). Almost all
of their content needs plasmashell, which Zaldros does not run — but the Aurorae window decoration
and the icon pack do not, so those two are vendored and used. These tests fail if the wiring, the
ISO package that provides the Aurorae engine, or the licence notice goes missing, and if anyone
quietly pulls in a part that would drag plasmashell into the image.
"""

from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
THEME = REPO / "system" / "theme" / "install-visual-theme.sh"
BUILD = REPO / "build" / "iso" / "build-iso.sh"
ASSETS = REPO / "assets" / "themes"

AURORAE_FILES = ("decoration.svg", "close.svg", "maximize.svg", "minimize.svg", "restore.svg",
                 "metadata.desktop")


def test_both_aurorae_variants_are_vendored_complete() -> None:
    for variant, rc in (("Windows-Eleven", "Windows-Elevenrc"),
                        ("Windows-Eleven-Dark", "Windows-Eleven-Darkrc")):
        directory = ASSETS / "aurorae" / variant
        assert directory.is_dir(), f"missing Aurorae theme {variant}"
        missing = [name for name in (*AURORAE_FILES, rc) if not (directory / name).exists()]
        assert not missing, f"{variant} is incomplete: {missing}"


def test_borrowed_assets_carry_their_notice() -> None:
    notice = (ASSETS / "NOTICE.md").read_text()
    for source in ("store.kde.org/p/1977804", "store.kde.org/p/1984455", "store.kde.org/p/1977340"):
        assert source in notice, f"{source} is not recorded in the notice"
    assert "GPL-3.0" in notice
    assert "theme-assets-NOTICE.md" in THEME.read_text(), "notice must be installed into the image"


def test_kwin_uses_the_aurorae_decoration() -> None:
    theme = THEME.read_text()
    assert 'AURORAE_THEME="Windows-Eleven-Dark"' in theme, "dark variant is the default decoration"
    assert "/usr/share/aurorae/themes" in theme, "themes must be installed where KWin looks"
    assert "library=$decoration_library" in theme and "theme=$decoration_theme" in theme, \
        "kwinrc must name the decoration it installed"
    assert "[org.kde.kdecoration2]" in theme, \
        "KWin 6 loads kdecoration3 plugins but still reads the kdecoration2 config group"


def test_iso_ships_the_engine_that_renders_the_decoration() -> None:
    """Aurorae is a package, not magic: without it KWin silently falls back to Breeze."""
    assert "kwin-style-aurorae" in BUILD.read_text(), \
        "kwin-style-aurorae provides org.kde.kwin.aurorae on Ubuntu 26.04"


def test_icon_pack_is_a_fallback_parent_not_a_replacement() -> None:
    theme = THEME.read_text()
    assert (ASSETS / "icons" / "Windows-Eleven-icons-4.8.8.tar.xz").exists()
    assert "Inherits=$FALLBACK_ICONS,hicolor" in theme, "our icons must still win over the pack"


def test_adopting_the_theme_did_not_adopt_the_plasma_session() -> None:
    """The audit's whole point: the borrowed parts must work under plain KWin.

    `full` deliberately installs the Plasma packages — it is the comparison profile — but no
    variant may *run* plasmashell, and the shared base must stay free of the Plasma stack.
    """
    build = BUILD.read_text()
    base = next(line for line in build.splitlines() if line.startswith("BASE="))
    for package in ("plasma-desktop", "plasma-workspace", "plasmashell", "kvantum"):
        assert package not in base, f"{package} does not belong in the shared base set"
    for line in build.splitlines():
        if line.strip().startswith("SESSION_EXEC="):
            assert "plasma" not in line, f"a variant would start plasmashell: {line.strip()}"
