# SPDX-License-Identifier: GPL-3.0-or-later
"""Zaldros Slides against a real LibreOffice Impress.

Unlike Writer, this engine really is installed in the build sandbox, so these tests start it,
build a deck, write PPTX, read it back and export a PDF. What they assert includes the parts of
the round trip that do **not** survive — an honest test says so rather than checking only what
works.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from zaldros_slides import (EngineError, ImpressEngine, impress_available,  # noqa: E402
                            soffice_path, uno_available)

pytestmark = pytest.mark.skipif(
    soffice_path() is None or not uno_available() or not impress_available(),
    reason="libreoffice-impress-nogui or the UNO bridge is missing in this interpreter")


@pytest.fixture(scope="module")
def engine():
    with ImpressEngine() as running:
        yield running


@pytest.fixture()
def deck(engine):
    presentation = engine.new_presentation()
    presentation.set_layout(0, 1)
    yield presentation
    presentation.close()


def test_a_new_presentation_starts_with_one_slide(deck):
    assert len(deck) == 1


def test_text_goes_into_the_layouts_own_placeholders(deck):
    deck.set_text(0, title="Zaldros", body="Слайд из движка")
    slide = deck.slides()[0]
    assert slide.title == "Zaldros" and "Слайд из движка" in slide.body


def test_a_layout_without_a_placeholder_refuses_instead_of_drawing_a_free_text_box(deck):
    deck.set_layout(0, 20)                       # blank
    with pytest.raises(EngineError) as error:
        deck.set_text(0, body="некуда положить")
    assert "заполнител" in str(error.value)


def test_adding_and_removing_slides_changes_the_deck_the_engine_holds(deck):
    deck.add_slide(layout=1)
    deck.add_slide(layout=1)
    assert len(deck) == 3
    deck.remove_slide(1)
    assert len(deck) == 2


def test_speaker_notes_are_the_engines_notes_page(deck):
    deck.set_notes(0, "сказать про честность")
    assert deck.slides()[0].notes == "сказать про честность"


def test_a_transition_is_written_and_read_back_from_the_engine(deck):
    deck.set_transition(0, 26)
    assert deck.transition(0) == 26


def test_pptx_round_trips_titles_and_notes(engine, deck, tmp_path):
    target = tmp_path / "deck.pptx"
    deck.set_text(0, title="Отчёт", body="Пункт")
    deck.set_notes(0, "заметка")
    deck.save_as(target)
    assert target.exists()
    reopened = engine.open(target)
    try:
        slide = reopened.slides()[0]
        assert slide.title == "Отчёт" and slide.notes == "заметка"
    finally:
        reopened.close()


def test_the_pptx_filter_does_not_carry_the_transition_and_we_do_not_claim_it_does(
        engine, deck, tmp_path):
    """Measured, not assumed: LibreOffice 7.4's PPTX export drops `TransitionType`, so a deck
    reopened from PPTX comes back with no transition. Recorded here so nobody claims otherwise."""
    target = tmp_path / "transition.pptx"
    deck.set_transition(0, 26)
    deck.save_as(target)
    reopened = engine.open(target)
    try:
        assert reopened.transition(0) == 0
    finally:
        reopened.close()


def test_pdf_export_produces_a_real_pdf(deck, tmp_path):
    target = tmp_path / "deck.pdf"
    deck.set_text(0, title="PDF")
    deck.export_pdf(target)
    assert target.exists() and target.read_bytes()[:4] == b"%PDF"


def test_an_unknown_format_is_refused_by_name(deck, tmp_path):
    with pytest.raises(EngineError) as error:
        deck.save_as(tmp_path / "deck.key")
    assert ".key" in str(error.value)


def test_a_slide_that_does_not_exist_is_an_error_not_a_silent_no_op(deck):
    with pytest.raises(EngineError):
        deck.set_text(9, title="нет такого слайда")
