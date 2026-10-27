# SPDX-License-Identifier: GPL-3.0-or-later
"""Qt view of Writer text, paragraph operations and selected character ranges."""
from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import (QAbstractListModel, QModelIndex, Property, QObject,
                            QTimer, Qt, QUrl, Signal, Slot)
from PySide6.QtGui import QFont, QFontDatabase, QSyntaxHighlighter, QTextCharFormat

from .engine import EngineError, WriterEngine, writer_available

REFERENCE = Path(__file__).resolve().parents[3] / 'system/theme/word-reference.json'
RIBBON_TABS = ('Файл', 'Главная', 'Вставка', 'Макет', 'Ссылки', 'Рецензирование', 'Вид')
STYLE_NAMES = {'Обычный': 'Standard', 'Заголовок 1': 'Heading 1',
               'Заголовок 2': 'Heading 2', 'Цитата': 'Quotations'}


def reference() -> dict:
    """Derived geometry, explicitly not a measured Word screenshot baseline."""
    with REFERENCE.open(encoding='utf-8') as handle:
        return json.load(handle)


class ParagraphRows(QAbstractListModel):
    """Keep editor delegates/carets alive during ordinary text/format updates."""
    def __init__(self, parent):
        super().__init__(parent)
        self.rows = []

    def roleNames(self):
        return {Qt.ItemDataRole.UserRole: b'paragraph'}

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if index.isValid() and role == Qt.ItemDataRole.UserRole:
            return self.rows[index.row()]

    def sync(self, rows):
        if len(rows) != len(self.rows):
            self.beginResetModel()
            self.rows = rows
            self.endResetModel()
        else:
            for index, row in enumerate(rows):
                if row != self.rows[index]:
                    self.rows[index] = row
                    position = self.index(index)
                    self.dataChanged.emit(position, position, [Qt.ItemDataRole.UserRole])


class RunHighlighter(QSyntaxHighlighter):
    """Paint engine character runs without rewriting text, selection or undo history."""
    def __init__(self, document):
        super().__init__(document)
        self.runs = []

    def highlightBlock(self, text):
        block_start = self.currentBlock().position()
        block_end = block_start + len(text.encode('utf-16-le')) // 2
        for run in self.runs:
            start = max(block_start, run['start'])
            end = min(block_end, run['start'] + run['length'])
            if start >= end:
                continue
            fmt = QTextCharFormat()
            if run['font']:
                fmt.setFontFamilies([run['font']])
            if run['size'] > 0:
                fmt.setFontPointSize(run['size'])
            if run['bold'] is not None:
                fmt.setFontWeight(QFont.Weight.Bold if run['bold'] else QFont.Weight.Normal)
            if run['italic'] is not None:
                fmt.setFontItalic(run['italic'])
            if run['underline'] is not None:
                fmt.setFontUnderline(run['underline'])
            self.setFormat(start - block_start, end - start, fmt)


class DocumentModel(QObject):
    changed = Signal()
    focusRequested = Signal(int, int)

    def __init__(self, document=None, engine: WriterEngine | None = None, path: str = '') -> None:
        super().__init__()
        self._engine = engine
        self._document = document
        self._paragraphs: list[dict] = []
        self._selected = 0
        self._status = '' if document is not None else self._missing_reason()
        self._path = str(Path(path).resolve()) if document is not None and path else ''
        self._modified = False
        self._drafts = {}
        self._text_selection = (0, 0)
        self._range_format = {}
        self._highlighters = {}
        self._selection_timer = QTimer(self)
        self._selection_timer.setSingleShot(True)
        self._selection_timer.setInterval(75)
        self._selection_timer.timeout.connect(self._read_selection)
        self._rows = ParagraphRows(self)
        self._flush_timer = QTimer(self)
        self._flush_timer.setSingleShot(True)
        self._flush_timer.setInterval(180)
        self._flush_timer.timeout.connect(self.flushEdits)
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
            self._sync_rows()
            self.changed.emit()
            return
        try:
            self._paragraphs = [vars(item).copy() for item in self._document.paragraphs()]
            if not 0 <= self._selected < len(self._paragraphs):
                self._selected = 0
            self._status = ''
        except EngineError as error:
            # Keep the last readback and any unsent draft if the engine is unavailable.
            self._status = str(error)
        self._sync_rows()
        if self.hasTextSelection:
            self._range_format = {}
            self._selection_timer.start()
        self.changed.emit()

    def _sync_rows(self):
        self._rows.sync([{**item, 'editorText': self._drafts.get(item['index'], item['text'])}
                         for item in self._paragraphs])
        for index, highlighter in list(self._highlighters.items()):
            try:
                highlighter.runs = (self._paragraphs[index].get('runs', [])
                                    if index not in self._drafts else [])
                highlighter.rehighlight()
            except (RuntimeError, IndexError):
                self._highlighters.pop(index, None)  # editor destroyed by a structural reset

    @Slot(int, QObject)
    def attachEditor(self, index, quick_document):  # noqa: N802
        self._highlighters[index] = RunHighlighter(quick_document.textDocument())
        self._sync_rows()

    def _clear_selection(self):
        self._selection_timer.stop()
        self._text_selection = (0, 0)
        self._range_format = {}

    @Slot(int, int, int)
    def setTextSelection(self, index, start, end):  # noqa: N802
        if index != self._selected or not self.formatAvailable:
            return
        pair = (min(start, end), max(start, end))
        if pair == self._text_selection:
            return
        self._text_selection = pair
        self._range_format = {}
        self._selection_timer.start()
        self.changed.emit()

    def _read_selection(self):
        self._selection_timer.stop()
        if not self.hasTextSelection:
            return True
        if not self.flushEdits():
            return False
        self._selection_timer.stop()
        try:
            self._range_format = self._document.character_format(self._selected, *self._text_selection)
        except EngineError as error:
            self._range_format = {}
            self._status = str(error)
            self.changed.emit()
            return False
        self._status = ''
        self.changed.emit()
        return True

    @Slot(int, str, result=bool)
    def queueText(self, index: int, text: str) -> bool:  # noqa: N802
        if not self.live or not 0 <= index < len(self._paragraphs):
            return False
        self._clear_selection()
        if text == self._paragraphs[index]['text']:
            self._drafts.pop(index, None)
        else:
            self._drafts[index] = text
            self._modified = True
        self._sync_rows()
        self.changed.emit()
        self._flush_timer.start()
        return True

    @Slot(result=bool)
    def flushEdits(self) -> bool:  # noqa: N802
        self._flush_timer.stop()
        for index, text in list(self._drafts.items()):
            try:
                self._document.replace_paragraph_text(index, self._paragraphs[index]['text'], text)
            except EngineError as error:
                self._status = str(error)
                self.changed.emit()
                return False
            self.refresh()
            if self._status:
                return False
            self._drafts.pop(index)
            self._sync_rows()
            self.changed.emit()
        return True

    @Slot(int, int, result=bool)
    def splitParagraph(self, index: int, position: int) -> bool:  # noqa: N802
        self._clear_selection()
        if not self._edit('split_paragraph', index, position):
            return False
        self._selected = index + 1
        self.changed.emit()
        self.focusRequested.emit(self._selected, 0)
        return True

    @Slot(int, result=bool)
    def mergeParagraph(self, index: int) -> bool:  # noqa: N802
        self._clear_selection()
        if not 0 < index < len(self._paragraphs) or not self.flushEdits():
            return False
        position = len(self._paragraphs[index - 1]['text'].encode('utf-16-le')) // 2
        if not self._edit('merge_paragraph', index):
            return False
        self._selected = index - 1
        self.changed.emit()
        self.focusRequested.emit(self._selected, position)
        return True

    def _edit(self, action, *args, **kwargs) -> bool:
        if self._document is None or not self.flushEdits():
            return False
        self._modified = True
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
        if index == self._selected:
            return True
        if not self.flushEdits():
            self.focusRequested.emit(self._selected, 0)
            return False
        self._selected = index
        self._clear_selection()
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
        return self._apply_character_format(index, **{attribute: value})

    def _apply_character_format(self, index, **properties):
        if index == self._selected and self.hasTextSelection:
            if not self._read_selection():
                return False
            properties.update(zip(('start', 'end'), self._text_selection))
        if not self._edit('set_character_format', index, **properties):
            return False
        return self._read_selection()

    @Slot(str, result=bool)
    def applyFont(self, name: str) -> bool:  # noqa: N802
        return self._apply_character_format(self._selected, font=name)

    @Slot(float, result=bool)
    def applyFontSize(self, size: float) -> bool:  # noqa: N802
        return self._apply_character_format(self._selected, size=size)

    @Slot(int, result=bool)
    def applyAlignment(self, alignment: int) -> bool:  # noqa: N802
        return self._edit('set_alignment', self._selected, alignment)

    @Slot(str, result=bool)
    def saveAs(self, path: str) -> bool:  # noqa: N802
        if self._document is None or not self.flushEdits():
            return False
        try:
            self._path = str(self._document.save_as(path, overwrite=True))
        except EngineError as error:
            self._status = str(error)
            self.changed.emit()
            return False
        self._status = ''
        self._modified = False
        self.changed.emit()
        return True

    @Slot(str, result=bool)
    def exportPdf(self, path: str) -> bool:  # noqa: N802
        if self._document is None or not self.flushEdits():
            return False
        try:
            self._document.export_pdf(path)
        except EngineError as error:
            self._status = str(error)
            self.changed.emit()
            return False
        self._status = ''
        self.changed.emit()
        return True

    @Slot(QUrl, result=bool)
    def saveAsUrl(self, url: QUrl) -> bool:  # noqa: N802
        return self.saveAs(url.toLocalFile()) if url.isLocalFile() else False

    @Property('QVariantList', notify=changed)
    def paragraphs(self) -> list:
        return list(self._paragraphs)

    @Property(QObject, constant=True)
    def paragraphModel(self):  # noqa: N802
        return self._rows

    @Property(bool, notify=changed)
    def modified(self) -> bool:
        return self._modified

    @Property(bool, notify=changed)
    def pendingEdits(self) -> bool:  # noqa: N802
        return bool(self._drafts)

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
        if not self.formatAvailable:
            return {}
        base = self._paragraphs[self._selected].copy()
        if self.hasTextSelection:
            unknown = dict(font='', size=0, bold=None, italic=None, underline=None)
            return {**base, **(self._range_format or unknown)}
        return base

    @Property(bool, notify=changed)
    def hasTextSelection(self) -> bool:  # noqa: N802
        return self._text_selection[1] > self._text_selection[0]

    @Property(int, notify=changed)
    def selectionLength(self) -> int:  # noqa: N802
        return self._text_selection[1] - self._text_selection[0]

    @Property(bool, notify=changed)
    def characterFormatAvailable(self) -> bool:  # noqa: N802
        return self.formatAvailable and (not self.hasTextSelection or bool(self._range_format))

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
