# SPDX-License-Identifier: GPL-3.0-or-later
"""The Writer bridge. Engine tests run only where the engine really is.

`soffice` on PATH proves nothing: this build sandbox has `libreoffice-calc-nogui` and no Writer at
all, and a suite that passed here would prove nothing about word processing. The engine tests skip
loudly; everything that can be checked without Writer is checked.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from zaldros_writer import (EngineError, WriterEngine, convert, soffice_path,  # noqa: E402
                            uno_available, writer_available)

needs_engine = pytest.mark.skipif(
    soffice_path() is None or not uno_available() or not writer_available(),
    reason="libreoffice-writer-nogui or the UNO bridge is missing in this interpreter")


# --- what holds without an engine ----------------------------------------------------------------
def test_the_filter_names_are_the_engines_own_strings():
    assert FILTERS_SUBSET.issubset(set(__import__("zaldros_writer").engine.FILTERS))


FILTERS_SUBSET = {".docx", ".odt", ".pdf", ".doc", ".rtf", ".txt"}


def test_an_unknown_format_is_refused_by_name():
    with pytest.raises(EngineError) as error:
        convert(__file__, ".wpd")
    assert ".wpd" in str(error.value)


def test_converting_a_file_that_does_not_exist_says_which_file():
    if soffice_path() is None:
        pytest.skip("no engine binary at all")
    with pytest.raises(EngineError) as error:
        convert("/tmp/zaldros-nonexistent.docx", ".pdf")
    assert "zaldros-nonexistent" in str(error.value)


def test_without_writer_the_error_names_the_missing_package_not_the_engines_riddle(monkeypatch):
    """LibreOffice answers «type detection failed», which tells a user nothing."""
    # Exercise the absent-component path even on the fully provisioned CI runner.
    # new_document checks this before requesting a desktop; no engine is needed.
    monkeypatch.setattr("zaldros_writer.engine.writer_available", lambda: False)
    engine = WriterEngine()
    with pytest.raises(EngineError) as error:
        engine.new_document()
    assert "libreoffice-writer-nogui" in str(error.value)


# --- with a real Writer ------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def engine():
    with WriterEngine() as running:
        yield running


@needs_engine
def test_the_engine_holds_the_text_not_us(engine):
    document = engine.new_document()
    try:
        document.append("Здравствуйте")
        document.append_paragraph("Второй абзац")
        assert [item.text for item in document.paragraphs()] == ["Здравствуйте", "Второй абзац"]
    finally:
        document.close()


@needs_engine
def test_a_heading_is_the_engines_own_style_not_bold_text(engine):
    document = engine.new_document()
    try:
        document.append("Заголовок")
        document.set_paragraph_style(0, "Heading 1")
        assert document.paragraphs()[0].style == "Heading 1"
    finally:
        document.close()


@needs_engine
def test_docx_round_trips_through_the_engine(tmp_path, engine):
    document = engine.new_document()
    target = tmp_path / "letter.docx"
    try:
        document.append("Договор №1")
        document.save_as(target)
        assert target.exists()
    finally:
        document.close()
    reopened = engine.open(target)
    try:
        assert "Договор №1" in reopened.text
    finally:
        reopened.close()


@needs_engine
def test_pdf_export_produces_a_real_pdf(tmp_path, engine):
    document = engine.new_document()
    target = tmp_path / "report.pdf"
    try:
        document.append("PDF")
        document.export_pdf(target)
    finally:
        document.close()
    assert target.exists() and target.read_bytes()[:4] == b"%PDF"


@needs_engine
def test_the_page_count_comes_from_the_engines_pagination(engine):
    document = engine.new_document()
    try:
        for _ in range(200):
            document.append_paragraph("строка")
        assert document.page_count() >= 2
    finally:
        document.close()


@needs_engine
def test_a_table_is_a_real_writer_table(engine, tmp_path):
    document = engine.new_document()
    target = tmp_path / "table.odt"
    try:
        document.append("Before")
        document.insert_table(2, 2, [["a", "b"], ["c", "d"]])
        document.append_paragraph("After")
        document.save_as(target)
    finally:
        document.close()
    reopened = engine.open(target)
    try:
        assert reopened._doc.TextTables.Count == 1
        assert reopened.text.split() == ["Before", "a", "b", "c", "d", "After"]
    finally:
        reopened.close()


@needs_engine
def test_italic_is_written_and_read_as_the_uno_font_slant_enum(engine):
    document = engine.new_document()
    try:
        document.append("Курсив")
        document.set_character_format(0, italic=True)
        assert document.paragraphs()[0].italic is True
        document.set_character_format(0, italic=False)
        assert document.paragraphs()[0].italic is False
    finally:
        document.close()


@needs_engine
def test_paragraph_indexes_after_a_table_select_the_same_paragraph_for_formatting(engine):
    document = engine.new_document()
    try:
        document.append("Before")
        document.insert_table(1, 1, [["cell"]])
        document.append_paragraph("After")
        paragraphs = document.paragraphs()
        assert [p.index for p in paragraphs] == list(range(len(paragraphs)))
        target = next(p for p in paragraphs if p.text == "After")
        document.set_paragraph_style(target.index, "Heading 1")
        assert next(p for p in document.paragraphs() if p.text == "After").style == "Heading 1"
        assert document.paragraphs()[0].style != "Heading 1"
    finally:
        document.close()


@needs_engine
@pytest.mark.parametrize('suffix', ['.odt', '.docx'])
def test_font_size_and_alignment_round_trip_and_invalid_input_is_unchanged(engine, tmp_path, suffix):
    document = engine.new_document()
    target = tmp_path / ('formatting' + suffix)
    try:
        document.append('Before')
        document.insert_table(1, 1, [['cell']])
        document.append_paragraph('After')
        index = next(p.index for p in document.paragraphs() if p.text == 'After')
        document.set_character_format(index, font='Liberation Sans', size=13.5)
        document.set_alignment(index, 3)
        for size in (0, 401, float('nan'), float('inf')):
            with pytest.raises(EngineError):
                document.set_character_format(index, size=size)
        with pytest.raises(EngineError):
            document.set_character_format(index, font=' ')
        with pytest.raises(EngineError):
            document.set_alignment(index, 99)
        with pytest.raises(EngineError):
            document.set_alignment(-1, 3)
        document.save_as(target)
    finally:
        document.close()
    reopened = engine.open(target)
    try:
        after = next(p for p in reopened.paragraphs() if p.text == 'After')
        assert after.font == 'Liberation Sans'
        assert after.size == 13.5
        assert after.alignment == 3
        assert reopened.paragraphs()[0].alignment == 0
    finally:
        reopened.close()


@needs_engine
def test_mixed_character_properties_can_be_read_and_replaced(engine):
    document = engine.new_document()
    try:
        document.append('Mixed paragraph')
        cursor = document._doc.Text.createTextCursor()
        cursor.gotoStart(False)
        cursor.goRight(5, True)
        cursor.CharWeight = 150.0
        cursor.CharHeight = 24.0
        assert document.paragraphs()[0].text == 'Mixed paragraph'
        document.set_character_format(0, bold=False, size=12)
        paragraph = document.paragraphs()[0]
        assert paragraph.bold is False and paragraph.size == 12
    finally:
        document.close()
