"""Our own window decoration: generated from the measurements, complete, and actually selected.

Until 2026-08-27 the title bars of real applications were drawn by a GPL-3 theme from the KDE
store. ADR-0010 allows exactly one borrowed pack (the cursors), so the decoration is ours now:
`tools/theme/make_aurorae.py` writes the nine slices and the five button states from
`system/theme/win11-reference.json`. These tests fail if the files drift from those numbers, if a
piece KWin needs is missing, or if the borrowed theme comes back.
"""

import importlib.util
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
AURORAE = REPO / "assets" / "themes" / "aurorae"
THEME_SH = (REPO / "system" / "theme" / "install-visual-theme.sh").read_text()
GENERATOR = REPO / "tools" / "theme" / "make_aurorae.py"

SLICES = ("topleft", "top", "topright", "left", "center", "right",
          "bottomleft", "bottom", "bottomright")
BUTTON_STATES = ("active-center", "hover-center", "pressed-center", "deactivated-center",
                 "inactive-center")


def _generator():
    spec = importlib.util.spec_from_file_location("make_aurorae", GENERATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gen = _generator()


def test_both_variants_are_complete():
    for variant in ("Zaldros", "Zaldros-Dark"):
        directory = AURORAE / variant
        assert directory.is_dir(), f"missing {variant}"
        for name in ("decoration.svg", "metadata.desktop", f"{variant}rc", *(f"{b}.svg" for b in gen.BUTTONS)):
            assert (directory / name).is_file(), f"{variant} is missing {name}"


def test_the_decoration_has_every_slice_kwin_asks_for():
    svg = (AURORAE / "Zaldros-Dark" / "decoration.svg").read_text()
    for slice_name in SLICES:
        assert f'id="decoration-{slice_name}"' in svg
        assert f'id="decoration-inactive-{slice_name}"' in svg
    for extra in ("shadow_active", "shadow_inactive", "hint-top-margin"):
        assert f'id="{extra}"' in svg


def test_every_button_has_every_state():
    for kind in gen.BUTTONS:
        svg = (AURORAE / "Zaldros-Dark" / f"{kind}.svg").read_text()
        for state in BUTTON_STATES:
            assert f'id="{state}"' in svg, f"{kind}.svg has no {state}"


def test_the_numbers_come_from_the_reference_not_from_taste():
    window = gen.reference()
    rc = (AURORAE / "Zaldros-Dark" / "Zaldros-Darkrc").read_text()
    assert f"TitleHeight={window['title_bar_height']}" in rc
    assert f"ButtonWidth={window['caption_button_width']}" in rc
    assert f"ButtonHeight={window['caption_button_height']}" in rc
    svg = (AURORAE / "Zaldros-Dark" / "decoration.svg").read_text()
    radius = window["corner_radius"]
    assert f"Q0,0 {radius},0" in svg or f"Q0,{radius}" in svg or f",{radius} " in svg


def test_the_files_on_disk_are_what_the_generator_writes(tmp_path):
    """A hand-edited SVG would silently drift from the measurements; regenerate instead."""
    window = gen.reference()
    for variant in ("Zaldros", "Zaldros-Dark"):
        gen.write_theme(variant, tmp_path, window)
        for path in sorted((tmp_path / variant).iterdir()):
            committed = AURORAE / variant / path.name
            assert committed.read_text() == path.read_text(), f"{committed} is out of date"


def test_kwin_selects_our_decoration_and_the_borrowed_one_is_gone():
    assert 'AURORAE_THEME="Zaldros-Dark"' in THEME_SH
    assert 'AURORAE_THEME="Zaldros"' in THEME_SH          # the light variant
    assert not (AURORAE / "Windows-Eleven").exists()
    assert not (AURORAE / "Windows-Eleven-Dark").exists()
    assert "[org.kde.kdecoration2]" in THEME_SH
    notice = (REPO / "assets" / "themes" / "NOTICE.md").read_text()
    assert "aurorae/Windows-Eleven" not in re.sub(r"^>.*$", "", notice, flags=re.M)


def test_corners_are_rounded_on_every_window():
    """The maintainer's standing request; a maximised window keeps its decoration for it."""
    assert "BorderlessMaximizedWindows=false" in THEME_SH
    window = gen.reference()
    assert window["corner_radius"] == 8
