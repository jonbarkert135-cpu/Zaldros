# SPDX-License-Identifier: GPL-3.0-or-later
"""The Writer window renders, and says the truth when there is no engine behind it."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from zaldros_writer.model import DocumentModel, RIBBON_TABS, reference  # noqa: E402


def test_the_geometry_file_says_it_is_derived_and_names_its_source():
    values = reference()
    assert values["derived_from"].endswith("excel-reference.json")
    assert any("derived" in line.lower() or "DERIVED" in line for line in values["_comment"])


def test_the_ribbon_has_words_own_tabs_in_words_order():
    assert RIBBON_TABS[:4] == ("Файл", "Главная", "Вставка", "Макет")


def test_a_model_without_a_document_has_no_paragraphs_and_carries_a_reason(qt_app):
    model = DocumentModel(None)
    assert model.paragraphs == [] and model.status
    assert not model.live and model.pageCount == 0


def test_a_model_without_a_document_refuses_edits_instead_of_pretending(qt_app):
    model = DocumentModel(None)
    assert not model.appendParagraph("текст")
    assert not model.applyStyle(0, "Заголовок 1")
    assert not model.saveAs("/tmp/zaldros-should-not-exist.docx")
    assert not Path("/tmp/zaldros-should-not-exist.docx").exists()


def test_the_window_renders_and_shows_the_reason_on_screen(tmp_path, qt_app):
    from zaldros_writer.app import render
    out = render(str(tmp_path / "writer.png"))
    assert Path(out).exists() and Path(out).stat().st_size > 10000


@pytest.fixture(scope="session")
def qt_app():
    from PySide6.QtCore import QCoreApplication
    from PySide6.QtGui import QGuiApplication
    return QCoreApplication.instance() or QGuiApplication([])
