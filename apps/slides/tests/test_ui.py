# SPDX-License-Identifier: GPL-3.0-or-later
"""The Slides window, with and without an engine behind it."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from zaldros_slides.model import DeckModel, RIBBON_TABS  # noqa: E402


@pytest.fixture(scope="session")
def qt_app():
    from PySide6.QtCore import QCoreApplication
    from PySide6.QtGui import QGuiApplication
    return QCoreApplication.instance() or QGuiApplication([])


def test_the_ribbon_has_powerpoints_tabs(qt_app):
    assert RIBBON_TABS[:5] == ("Файл", "Главная", "Вставка", "Конструктор", "Переходы")


def test_without_an_engine_the_deck_is_empty_and_says_why(qt_app):
    model = DeckModel(None)
    assert model.slides == [] and model.status and not model.live
    assert not model.addSlide(1) and not model.setText(0, "t", "b")


def test_the_window_renders(tmp_path, qt_app):
    from zaldros_slides.app import render
    out = render(str(tmp_path / "slides.png"))
    assert Path(out).exists() and Path(out).stat().st_size > 10000


def test_the_model_shows_what_the_engine_holds(tmp_path, qt_app):
    from zaldros_slides.engine import ImpressEngine, impress_available, uno_available
    if not (impress_available() and uno_available()):
        pytest.skip("no Impress engine here")
    with ImpressEngine() as engine:
        deck = engine.new_presentation()
        deck.set_layout(0, 1)
        deck.set_text(0, title="Заголовок", body="Текст")
        model = DeckModel(deck)
        assert model.live and model.current["title"] == "Заголовок"
        assert model.addSlide(1) and len(model.slides) == 2
        deck.close()
