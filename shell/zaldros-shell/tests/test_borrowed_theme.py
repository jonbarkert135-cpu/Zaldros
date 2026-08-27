"""Guard: the borrowed Plasma-store assets stay wired, licensed and inside our architecture.

Run #29 audited two "windows-eleven" Plasma global themes (docs/PLASMA_THEME_AUDIT.md). Almost all
of their content needs plasmashell, which Zaldros does not run. The Aurorae decoration was vendored
from them until 2026-08-27 and is now ours (tests/test_aurorae_theme.py); what remains borrowed is
the icon pack and the Kvantum style. These tests fail if that wiring, the ISO package that provides
the Aurorae engine, or a licence notice goes missing, and if anyone quietly pulls in a part that
would drag plasmashell into the image.
"""

from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
THEME = REPO / "system" / "theme" / "install-visual-theme.sh"
BUILD = REPO / "build" / "iso" / "build-iso.sh"
ASSETS = REPO / "assets" / "themes"

def test_borrowed_assets_carry_their_notice() -> None:
    notice = (ASSETS / "NOTICE.md").read_text()
    # the two Aurorae decorations left the tree on 2026-08-27 (ours replaced them); the icon pack
    # and the Kvantum style are still borrowed and still have to be named.
    for source in ("store.kde.org/p/1977340", "github.com/Jeysef/KDE-Windows-Modern"):
        assert source in notice, f"{source} is not recorded in the notice"
    assert "GPL-3.0" in notice
    assert "theme-assets-NOTICE.md" in THEME.read_text(), "notice must be installed into the image"


def test_kwin_uses_our_own_aurorae_decoration() -> None:
    theme = THEME.read_text()
    assert 'AURORAE_THEME="Zaldros-Dark"' in theme, "our dark decoration is the default"
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
    for package in ("plasma-desktop", "plasma-workspace", "plasmashell"):
        assert package not in base, f"{package} does not belong in the shared base set"
    # qt6-style-kvantum is the exception that proves the rule: a Qt style engine, no Plasma session.
    assert "plasma" not in base.replace("qt6-style-kvantum", ""), \
        "the base set must stay free of the Plasma stack"
    for line in build.splitlines():
        if line.strip().startswith("SESSION_EXEC="):
            assert "plasma" not in line, f"a variant would start plasmashell: {line.strip()}"


def test_the_colour_scheme_kdeglobals_names_is_actually_installed() -> None:
    """Run #29 live boot log: 'Could not find color scheme "ZaldrosDark" falling back to
    BreezeLight' — kdeglobals pointed at a scheme no file provided, so every KDE app ran light."""
    theme = THEME.read_text()
    assert '"$DEST/usr/share/color-schemes/$c_scheme_name.colors"' in theme, \
        "the scheme file must be installed where KDE looks for it"
    assert theme.count("ColorScheme=$c_scheme_name") >= 2, \
        "kdeglobals and the scheme file must name the same scheme"
    assert "c_scheme_name=\"ZaldrosDark\"" in theme and "c_scheme_name=\"ZaldrosLight\"" in theme


def test_kvantum_style_is_installed_selected_and_licensed() -> None:
    """QWidget applications (Dolphin, Konsole) get their look from the Qt style, not from us."""
    theme = THEME.read_text()
    kvantum = ASSETS / "kvantum" / "Windows-modern"
    for name in ("Windows-modern.kvconfig", "Windows-modernDark.kvconfig",
                 "Windows-modern.svg", "Windows-modernDark.svg"):
        assert (kvantum / name).exists(), f"missing Kvantum file {name}"
    assert (ASSETS / "kvantum" / "LICENSE").exists()
    assert (ASSETS / "kvantum" / "ATTRIBUTION.md").exists(), "upstream lists its own ancestry"
    assert "/usr/share/Kvantum" in theme, "the theme must be installed where Kvantum looks"
    assert "/etc/xdg/Kvantum/kvantum.kvconfig" in theme and "/etc/skel/.config/Kvantum" in theme, \
        "a live user has no home yet, so the default must exist system-wide and in the skeleton"
    assert "widgetStyle=$widget_style" in theme, "kdeglobals must select the style we installed"
    assert 'KVANTUM_STYLE="kvantum-dark"' in theme
    assert "qt6-style-kvantum" in BUILD.read_text(), \
        "qt6-style-kvantum provides the engine; without it the style name is ignored"


def test_the_chroot_can_unpack_what_we_ship_it() -> None:
    """Run #29 ISO failure: the icon pack is .tar.xz and the minimal rootfs had no xz binary,
    so `tar` exited with 'xz: Cannot exec' and the theme step killed the build."""
    build = BUILD.read_text()
    pack = ASSETS / "icons" / "Windows-Eleven-icons-4.8.8.tar.xz"
    if pack.suffix == ".xz":
        start = build.index("step theme chroot")
        theme_step = build[start:build.index("install-visual-theme.sh", start)]
        assert "xz-utils" in theme_step, "the theme step must be able to unpack a .tar.xz"
