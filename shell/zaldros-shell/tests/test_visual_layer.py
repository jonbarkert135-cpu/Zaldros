"""Guards for the visual layer the ISO installs (ADR-0010: cursors are the only borrowed pack).

Two classes of regression are covered:

1. A theme pack sneaking back into the image. The owner's decision on 2026-08-26 was that Zaldros
   draws its own look and takes only the cursor theme from upstream; a stray clone of a GTK or icon
   theme in the build scripts would silently undo that.
2. The cursor theme being configured but never installed. Runs #17-#25 logged "no cursor theme"
   because visual.conf named one while nothing copied the files or created the `default` alias.
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
FETCH = REPO / "system" / "theme" / "fetch-sources.sh"
INSTALL = REPO / "system" / "theme" / "install-visual-theme.sh"
BUILD = REPO / "build" / "iso" / "build-iso.sh"
SELFTEST = REPO / "build" / "iso" / "selftest.py"

BANNED_UPSTREAM = ["Win11-gtk-theme", "Win11-icon-theme", "Fluent-gtk-theme", "Orchis", "WhiteSur"]


def test_only_the_cursor_pack_is_fetched() -> None:
    fetch = FETCH.read_text()
    cloned = set(re.findall(r"https://github\.com/[\w.-]+/([\w.-]+)\.git", fetch))
    assert cloned == {"Fluent-icon-theme"}, f"unexpected upstream clones: {sorted(cloned)}"
    # ...and from that repository, only the cursors.
    assert "sparse-checkout set --no-cone cursors" in fetch


def test_no_third_party_theme_pack_is_installed() -> None:
    for path in (INSTALL, BUILD):
        text = path.read_text()
        for name in BANNED_UPSTREAM:
            # A comment explaining the decision is fine; an install or clone of it is not.
            lines = [ln for ln in text.splitlines()
                     if name in ln and not ln.lstrip().startswith("#")]
            assert not lines, f"{path.name} still uses {name}: {lines}"


def test_cursor_theme_is_installed_and_made_the_default() -> None:
    install = INSTALL.read_text()
    assert "cursors/dist-dark" in install and "cursors/dist" in install, "cursor files never copied"
    assert "/default/index.theme" in install, "no default cursor alias — Xcursor ignores the theme"
    assert "kcminputrc" in install, "KDE reads the pointer from kcminputrc, not kdeglobals"
    assert "XCURSOR_THEME" in BUILD.read_text(), "the session must export XCURSOR_THEME"


def test_the_icon_theme_is_built_from_our_own_assets() -> None:
    install = INSTALL.read_text()
    assert '$ICONS/Zaldros' in install and "Name=Zaldros" in install
    for directory in ("apps", "places", "fluent"):
        assert f'"$ASSETS/icons/{directory}/"' in install, f"{directory} icons are not installed"
    assert 'icon_theme="Zaldros"' in install, "the built theme must be the one the system uses"
    assert "icon_theme=$icon_theme" in install, "visual.conf must point the shell at our own theme"


def test_the_selftest_reports_the_visual_layer_as_evidence() -> None:
    selftest = SELFTEST.read_text()
    assert '"visual_layer": visual_layer()' in selftest
    for key in ("cursor_theme_installed", "cursor_shapes", "icon_theme_installed"):
        assert key in selftest, f"self-test does not report {key}"


def test_every_icon_the_theme_ships_exists_in_the_repository() -> None:
    for directory in ("apps", "places", "fluent"):
        source = REPO / "assets" / "icons" / directory
        assert source.is_dir(), f"missing {source}"
        assert list(source.glob("*.svg")), f"no SVGs in {source}"
