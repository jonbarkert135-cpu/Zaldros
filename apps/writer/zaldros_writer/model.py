# SPDX-License-Identifier: GPL-3.0-or-later
"""Qt view of the real Writer document; formatting targets a whole paragraph."""
from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtGui import QFontDatabase

from .engine import EngineError, WriterEngine, writer_available

REFERENCE = Path(__file__).resolve().parents[3] / 'system/theme/word-reference.json'
RIBBON_TABS = ('Файл', 'Главная', 'Вставка', 'Макет', 'Ссылки', 'Рецензирование', 'Вид')
STYLE_NAMES = {'Обычный': 'Default Paragraph Style', 'Заголовок 1': 'Heading 1',
               'Заголовок 2': 'Heading 2', 'Цитата': 'Quotations'}


def reference() -> dict:
    """Derived geometry, explicitly not a measured Word screenshot baseline."""
    with REFERENCE.open(encoding='utf-8') as handle:
        return json.load(handle)


class DocumentModel(QObject):
    changed = Signal()

    def __init__(self, document=None, engine: WriterEngine | None = None) -> None:
        super().__init__()
        self._engine = engine
        self._document = document
        self._paragraphs: list[dict] = []
        self._selected = 0
        self._status = '' if document is not None else self._missing_reason()
        self._path = ''
        if document is not None:
            self.refresh()

    def _missing_reason(self) -> str:
        if not writer_available():
            return self.tr('Движок Writer не установлен (пакет libreoffice-writer-nogui)')
        return self.tr('Документ не открыт')

    @Slot()
    def refresh(self) -> None:
        if self._document is None:
            self._paragraphs = []
            self.changed.emit()
            return
        try:
            self._paragraphs = [vars(item).copy() for item in self._document.paragraphs()]
            if not 0 <= self._selected < len(self._paragraphs):
                self._selected = 0
            self._status = ''
        except EngineError as error:
            self._paragraphs = []
            self._status = str(error)
        self.changed.emit()

    def _edit(self, action, *args, **kwargs) -> bool:
        if self._document is None:
            return False
        try:
            getattr(self._document, action)(*args, **kwargs)
        except EngineError as error:
            # Read back even after a partial engine failure; never leave stale pressed states.
            self.refresh()
            self._status = str(error)
            self.changed.emit()
            return False
        self.refresh()
        return not self._status

    @Slot(int, result=bool)
    def selectParagraph(self, index: int) -> bool:  # noqa: N802
        if not 0 <= index < len(self._paragraphs):
            return False
        self._selected = index
        self.changed.emit()
        return True

    @Slot(str, result=bool)
    def appendParagraph(self, text: str) -> bool:  # noqa: N802
        return self._edit('append_paragraph', text)

    @Slot(int, str, result=bool)
    def applyStyle(self, index: int, name: str) -> bool:  # noqa: N802
        return self._edit('set_paragraph_style', index, STYLE_NAMES.get(name, name))

    @Slot(int, str, bool, result=bool)
    def applyFormat(self, index: int, attribute: str, value: bool) -> bool:  # noqa: N802
        if attribute not in ('bold', 'italic', 'underline'):
            return False
        return self._edit('set_character_format', index, **{attribute: value})

    @Slot(str, result=bool)
    def applyFont(self, name: str) -> bool:  # noqa: N802
        return self._edit('set_character_format', self._selected, font=name)

    @Slot(float, result=bool)
    def applyFontSize(self, size: float) -> bool:  # noqa: N802
        return self._edit('set_character_format', self._selected, size=size)

    @Slot(int, result=bool)
    def applyAlignment(self, alignment: int) -> bool:  # noqa: N802
        return self._edit('set_alignment', self._selected, alignment)

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
        self._status = ''
        self.changed.emit()
        return True

    @Slot(str, result=bool)
    def exportPdf(self, path: str) -> bool:  # noqa: N802
        return self.saveAs(str(Path(path).with_suffix('.pdf')))

    @Property('QVariantList', notify=changed)
    def paragraphs(self) -> list:
        return list(self._paragraphs)

    @Property('QVariantList', constant=True)
    def tabs(self) -> list:
        return [self.tr('Файл'), self.tr('Главная'), self.tr('Вставка'), self.tr('Макет'),
                self.tr('Ссылки'), self.tr('Рецензирование'), self.tr('Вид')]

    @Property(int, notify=changed)
    def selectedParagraph(self) -> int:  # noqa: N802
        return self._selected

    @Property(bool, notify=changed)
    def formatAvailable(self) -> bool:  # noqa: N802
        return self.live and 0 <= self._selected < len(self._paragraphs)

    @Property('QVariantMap', notify=changed)
    def selection(self) -> dict:
        return self._paragraphs[self._selected].copy() if self.formatAvailable else {}

    @Property('QStringList', notify=changed)
    def fontFamilies(self) -> list[str]:  # noqa: N802
        families = set(QFontDatabase.families())
        if self.formatAvailable and self.selection['font']:
            families.add(self.selection['font'])
        return sorted(families)

    @Property(str, notify=changed)
    def status(self) -> str:
        return self._status

    @Property(str, notify=changed)
    def path(self) -> str:
        return self._path

    @Property(int, notify=changed)
    def wordCount(self) -> int:  # noqa: N802
        return sum(len(item['text'].split()) for item in self._paragraphs)

    @Property(int, notify=changed)
    def pageCount(self) -> int:  # noqa: N802
        if self._document is None:
            return 0
        try:
            return self._document.page_count()
        except EngineError:
            return 0

    @Property(bool, notify=changed)
    def live(self) -> bool:
        return self._document is not None
