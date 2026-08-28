# SPDX-License-Identifier: GPL-3.0-or-later
"""Qt model for the Zaldros Writer UI.

The model is a *view* of the engine, never a second source of truth. Without an engine it is an
empty document that says why it is empty — the chrome renders, and nothing pretends to be a
working word processor.
"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Property, QObject, Signal, Slot

from .engine import EngineError, WriterEngine, writer_available

REFERENCE = Path(__file__).resolve().parents[3] / "system" / "theme" / "word-reference.json"

# Word's Home tab, in Word's order. Buttons that we cannot yet ask the engine for are absent
# rather than drawn dead — a ribbon full of decoration is what this project does not build.
HOME_GROUPS = (
    ("Буфер обмена", ("Вставить", "Вырезать", "Копировать")),
    ("Шрифт", ("Полужирный", "Курсив", "Подчёркнутый", "Размер")),
    ("Абзац", ("По левому краю", "По центру", "По правому краю", "По ширине")),
    ("Стили", ("Обычный", "Заголовок 1", "Заголовок 2", "Цитата")),
)

RIBBON_TABS = ("Файл", "Главная", "Вставка", "Макет", "Ссылки", "Рецензирование", "Вид")

STYLE_NAMES = {"Обычный": "Default Paragraph Style", "Заголовок 1": "Heading 1",
               "Заголовок 2": "Heading 2", "Цитата": "Quotations"}


def reference() -> dict:
    """The measured Word geometry. A missing file is a bug, not a default to invent."""
    with REFERENCE.open(encoding="utf-8") as handle:
        return json.load(handle)


class DocumentModel(QObject):
    """One document, as the ribbon and the page canvas see it."""

    changed = Signal()

    def __init__(self, document=None, engine: WriterEngine | None = None) -> None:
        super().__init__()
        self._engine = engine
        self._document = document
        self._paragraphs: list[dict] = []
        self._status = "" if document is not None else self._missing_reason()
        self._path = ""
        if document is not None:
            self.refresh()

    @staticmethod
    def _missing_reason() -> str:
        if not writer_available():
            return "Движок Writer не установлен (пакет libreoffice-writer-nogui)"
        return "Документ не открыт"

    @Slot()
    def refresh(self) -> None:
        if self._document is None:
            self._paragraphs = []
            self.changed.emit()
            return
        try:
            self._paragraphs = [
                {"index": item.index, "text": item.text, "style": item.style,
                 "bold": item.bold, "italic": item.italic, "underline": item.underline,
                 "size": item.size, "alignment": item.alignment}
                for item in self._document.paragraphs()]
            self._status = ""
        except EngineError as error:
            self._paragraphs = []
            self._status = str(error)
        self.changed.emit()

    # --- editing -----------------------------------------------------------------------------
    @Slot(str, result=bool)
    def appendParagraph(self, text: str) -> bool:  # noqa: N802
        if self._document is None:
            return False
        self._document.append_paragraph(text)
        self.refresh()
        return True

    @Slot(int, str, result=bool)
    def applyStyle(self, index: int, name: str) -> bool:  # noqa: N802
        """«Заголовок 1» is applied as the engine's own style, not as bold 16 pt."""
        if self._document is None:
            return False
        try:
            self._document.set_paragraph_style(index, STYLE_NAMES.get(name, name))
        except EngineError as error:
            self._status = str(error)
            self.changed.emit()
            return False
        self.refresh()
        return True

    @Slot(int, str, bool, result=bool)
    def applyFormat(self, index: int, attribute: str, value: bool) -> bool:  # noqa: N802
        if self._document is None:
            return False
        keyword = {"bold": "bold", "italic": "italic", "underline": "underline"}.get(attribute)
        if keyword is None:
            return False
        self._document.set_character_format(index, **{keyword: value})
        self.refresh()
        return True

    @Slot(str, result=bool)
    def saveAs(self, path: str) -> bool:  # noqa: N802
        if self._document is None:
            return False
        try:
            self._path = str(self._document.save_as(path))
        except EngineError as error:
            self._status = str(error)
            self.changed.emit()
            return False
        self.changed.emit()
        return True

    @Slot(str, result=bool)
    def exportPdf(self, path: str) -> bool:  # noqa: N802
        return self.saveAs(str(Path(path).with_suffix(".pdf")))

    # --- what QML draws ------------------------------------------------------------------------
    @Property("QVariantList", notify=changed)
    def paragraphs(self) -> list:
        return list(self._paragraphs)

    @Property("QVariantList", constant=True)
    def tabs(self) -> list:
        return list(RIBBON_TABS)

    @Property("QVariantList", constant=True)
    def groups(self) -> list:
        return [{"title": title, "commands": list(commands)} for title, commands in HOME_GROUPS]

    @Property(str, notify=changed)
    def status(self) -> str:
        return self._status

    @Property(str, notify=changed)
    def path(self) -> str:
        return self._path

    @Property(int, notify=changed)
    def wordCount(self) -> int:  # noqa: N802
        return sum(len(item["text"].split()) for item in self._paragraphs)

    @Property(int, notify=changed)
    def pageCount(self) -> int:  # noqa: N802
        """The engine's pagination, or 0 — never a guess from character counts."""
        if self._document is None:
            return 0
        try:
            return self._document.page_count()
        except EngineError:
            return 0

    @Property(bool, notify=changed)
    def live(self) -> bool:
        return self._document is not None
