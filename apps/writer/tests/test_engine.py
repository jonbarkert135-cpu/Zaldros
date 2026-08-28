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


def test_without_writer_the_error_names_the_missing_package_not_the_engines_riddle():
    """LibreOffice answers «type detection failed», which tells a user nothing."""
    if writer_available():
        pytest.skip("Writer is installed here")
    engine = WriterEngine()
    try:
        engine.start()
    except EngineError as error:
        assert "soffice" in str(error) or "UNO" in str(error)
        return
    try:
        with pytest.raises(EngineError) as error:
            engine.new_document()
        assert "libreoffice-writer-nogui" in str(error.value)
    finally:
        engine.stop()


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
        document.insert_table(2, 2, [["a", "b"], ["c", "d"]])
        document.save_as(target)
    finally:
        document.close()
    reopened = engine.open(target)
    try:
        assert "a" in reopened.text and "d" in reopened.text
    finally:
        reopened.close()
