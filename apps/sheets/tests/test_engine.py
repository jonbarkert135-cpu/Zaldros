"""The engine bridge, tested against the real engine.

These tests start a real headless LibreOffice and let it do the arithmetic. If the engine or the
UNO bridge is absent the tests skip loudly instead of pretending to pass — a green run with no
engine would prove nothing about the one thing this module does.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from zaldros_sheets import CalcEngine, EngineError, soffice_path, uno_available  # noqa: E402

pytestmark = pytest.mark.skipif(
    soffice_path() is None or not uno_available(),
    reason="no LibreOffice engine or no UNO bridge in this interpreter",
)


@pytest.fixture(scope="module")
def engine():
    with CalcEngine() as running:
        yield running


def test_the_engine_computes_the_formula_not_us(engine):
    book = engine.new_workbook()
    try:
        book.set_value(0, 0, 2)
        book.set_value(1, 0, 40)
        cell = book.set_formula(2, 0, "=SUM(A1:A2)*1.5")
        assert cell.formula == "=SUM(A1:A2)*1.5"
        assert cell.value == pytest.approx(63.0)
        assert cell.kind == "formula"
    finally:
        book.close()


def test_a_formula_error_is_reported_by_the_engine_verbatim(engine):
    book = engine.new_workbook()
    try:
        cell = book.set_formula(0, 0, "=1/0")
        assert "Err" in cell.text or "#" in cell.text, cell.text
    finally:
        book.close()


def test_xlsx_round_trip_keeps_formula_and_text(engine, tmp_path):
    book = engine.new_workbook()
    try:
        book.set_value(0, 0, 7)
        book.set_formula(1, 0, "=A1*6")
        book.set_text(0, 1, "Zaldros Sheets")
        target = book.save_as(tmp_path / "round-trip.xlsx")
        assert target.stat().st_size > 0
    finally:
        book.close()

    again = engine.open(target)
    try:
        assert again.cell(1, 0).formula == "=A1*6"
        assert again.cell(1, 0).value == pytest.approx(42.0)
        assert again.cell(0, 1).text == "Zaldros Sheets"
    finally:
        again.close()


def test_typing_into_a_cell_lets_the_engine_decide_the_type(engine):
    book = engine.new_workbook()
    try:
        assert book.set_input(0, 0, "12.5").kind == "number"
        assert book.set_input(1, 0, "hello").kind == "text"
        assert book.set_input(2, 0, "=A1*2").value == pytest.approx(25.0)
    finally:
        book.close()


def test_an_unknown_format_is_refused_before_the_engine_is_asked(engine, tmp_path):
    book = engine.new_workbook()
    try:
        with pytest.raises(EngineError):
            book.save_as(tmp_path / "nope.qqq")
    finally:
        book.close()


def test_opening_a_missing_file_names_the_file(engine, tmp_path):
    with pytest.raises(EngineError) as caught:
        engine.open(tmp_path / "absent.xlsx")
    assert "absent.xlsx" in str(caught.value)


# --- typing into a cell, end to end ---------------------------------------------------------
def test_typing_a_formula_is_the_engines_decision_not_ours(engine):
    """`set_input` is what the in-cell editor and the formula bar call. The engine decides
    whether what was typed is a number, a text or a formula — we never parse it."""
    book = engine.new_workbook()
    try:
        book.set_input(0, 0, "7")
        book.set_input(1, 0, "8")
        cell = book.set_input(2, 0, "=A1+A2")
        assert cell.kind == "formula" and cell.value == 15
        assert book.set_input(3, 0, "просто текст").kind == "text"
        assert book.set_input(4, 0, "3,5").kind in ("number", "text")   # locale is the engine's
    finally:
        book.close()


def test_clearing_a_cell_leaves_it_empty_rather_than_showing_a_zero(engine):
    book = engine.new_workbook()
    try:
        book.set_input(0, 0, "42")
        cleared = book.set_input(0, 0, "")
        assert cleared.kind == "empty" and cleared.text == ""
    finally:
        book.close()


def test_the_editor_shows_the_formula_and_the_grid_shows_the_result(engine):
    book = engine.new_workbook()
    try:
        book.set_input(0, 0, "2")
        book.set_input(0, 1, "=A1*3")
        cell = book.cell(0, 1)
        assert cell.formula == "=A1*3" and cell.text == "6"
    finally:
        book.close()
