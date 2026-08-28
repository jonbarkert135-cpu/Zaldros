"""Qt models for the Zaldros Sheets UI.

The grid model is a *view* of the engine, never a second source of truth: `GridModel` holds a
cache of the visible cells and refills it from what the engine reports after every edit. Set
`engine=None` and it becomes an empty sheet — enough to render the chrome for a visual test
without starting LibreOffice, and honest about it (`engine_state` says so on screen).
"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import (QAbstractTableModel, QModelIndex, QObject, Property, Qt, Signal,
                            Slot)

REFERENCE = Path(__file__).resolve().parents[3] / "system" / "theme" / "excel-reference.json"


def reference() -> dict:
    """The measured Excel geometry. A missing file is a bug, not a default to invent."""
    with REFERENCE.open(encoding="utf-8") as handle:
        return json.load(handle)


def column_name(index: int) -> str:
    """0 -> A, 25 -> Z, 26 -> AA. Excel's own scheme."""
    name = ""
    index += 1
    while index:
        index, rest = divmod(index - 1, 26)
        name = chr(ord("A") + rest) + name
    return name


class GridModel(QAbstractTableModel):
    DisplayRole = Qt.ItemDataRole.DisplayRole
    AlignRole = Qt.ItemDataRole.UserRole + 1

    def __init__(self, rows: int = 40, columns: int = 16, workbook=None) -> None:
        super().__init__()
        self._rows = rows
        self._columns = columns
        self._workbook = workbook
        self._cache: dict[tuple[int, int], tuple[str, bool]] = {}
        if workbook is not None:
            self.refill()

    # --- Qt plumbing -------------------------------------------------------------------------
    def rowCount(self, _parent=QModelIndex()) -> int:
        return self._rows

    def columnCount(self, _parent=QModelIndex()) -> int:
        return self._columns

    def roleNames(self):
        return {self.DisplayRole: b"display", self.AlignRole: b"numeric"}

    def data(self, index, role=DisplayRole):
        entry = self._cache.get((index.row(), index.column()))
        if entry is None:
            return "" if role == self.DisplayRole else False
        text, numeric = entry
        return text if role == self.DisplayRole else numeric

    # --- the engine side ---------------------------------------------------------------------
    def refill(self) -> None:
        """Ask the engine what the visible window of cells contains. Nothing is computed here."""
        if self._workbook is None:
            return
        block = self._workbook.region(self._rows, self._columns)
        self._cache = {}
        for row in block:
            for cell in row:
                if cell.text:
                    self._cache[(cell.row, cell.column)] = (cell.text, cell.kind != "text")
        self.beginResetModel()
        self.endResetModel()

    @Slot(int, int, result=str)
    def cellText(self, row: int, column: int) -> str:
        entry = self._cache.get((row, column))
        return entry[0] if entry else ""

    @Slot(int, int, result=bool)
    def cellIsNumeric(self, row: int, column: int) -> bool:
        entry = self._cache.get((row, column))
        return bool(entry and entry[1])

    @Slot(int, int, result=str)
    def cellFormula(self, row: int, column: int) -> str:
        """What the formula bar and the in-cell editor show: the engine's own formula text."""
        return self.formula_at(row, column)

    @Slot(int, result=str)
    def columnName(self, index: int) -> str:
        return column_name(index)

    def formula_at(self, row: int, column: int) -> str:
        if self._workbook is None:
            return ""
        return self._workbook.cell(row, column).formula

    def commit(self, row: int, column: int, raw: str) -> str:
        """Send what the user typed to the engine and show what the engine made of it."""
        if self._workbook is None:
            self._cache[(row, column)] = (raw, False)
            self.dataChanged.emit(self.index(row, column), self.index(row, column))
            return raw
        cell = self._workbook.set_input(row, column, raw)
        self._cache[(row, column)] = (cell.text, cell.kind != "text")
        self.dataChanged.emit(self.index(row, column), self.index(row, column))
        return cell.text


class SheetsState(QObject):
    """What the window shows around the grid."""

    changed = Signal()

    def __init__(self, grid: GridModel, *, engine_state: str = "", sheets=("Sheet1",),
                 light: bool = True, document: str = "Book1") -> None:
        super().__init__()
        self._grid = grid
        self._row = 0
        self._column = 0
        self._engine_state = engine_state
        self._sheets = list(sheets)
        self._light = light
        self._document = document

    def _get(name, cast=str):  # noqa: N805 - tiny property factory
        def getter(self):
            return getattr(self, name)
        return getter

    @Property(str, notify=changed)
    def address(self) -> str:
        return f"{column_name(self._column)}{self._row + 1}"

    @Property(str, notify=changed)
    def formula(self) -> str:
        return self._grid.formula_at(self._row, self._column)

    @Property(str, notify=changed)
    def engineState(self) -> str:
        return self._engine_state

    @Property(str, notify=changed)
    def document(self) -> str:
        return self._document

    @Property(bool, notify=changed)
    def light(self) -> bool:
        return self._light

    @Property(list, notify=changed)
    def sheets(self) -> list:
        return self._sheets

    @Property(int, notify=changed)
    def selectedRow(self) -> int:
        return self._row

    @Property(int, notify=changed)
    def selectedColumn(self) -> int:
        return self._column

    @Slot(int, int)
    def select(self, row: int, column: int) -> None:
        self._row, self._column = row, column
        self.changed.emit()

    @Slot(str)
    def commit(self, raw: str) -> None:
        self._grid.commit(self._row, self._column, raw)
        self.changed.emit()
