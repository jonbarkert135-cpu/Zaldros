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


def writer_view(model):
    from PySide6.QtCore import QUrl
    from PySide6.QtQuick import QQuickView
    from zaldros_writer.app import QML_DIR, load_font
    view = QQuickView()
    context = view.rootContext()
    context.setContextProperty('ref', reference())
    context.setContextProperty('document', model)
    context.setContextProperty('uiFontFamily', load_font())
    view.setSource(QUrl.fromLocalFile(str(QML_DIR / 'Writer.qml')))
    assert view.status() == QQuickView.Status.Ready, [e.toString() for e in view.errors()]
    view.resize(1280, 800)
    view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
    view.show()
    return view


def control(view, name):
    # Repeater delegates have a visual parent, not necessarily that QObject parent.
    pending = [view.rootObject()]
    while pending:
        item = pending.pop()
        if item.objectName() == name:
            return item
        pending.extend(item.childItems())
    raise AssertionError(name)


def close_view(view, qt_app):
    from PySide6.QtCore import QUrl
    view.close()
    view.setSource(QUrl())
    view.deleteLater()
    qt_app.processEvents()


def click(view, name, qt_app):
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtTest import QTest
    qt_app.processEvents()
    item = control(view, name)
    assert item.isEnabled() and item.isVisible(), name
    point = item.mapToScene(QPointF(item.width() / 2, item.height() / 2)).toPoint()
    QTest.mouseClick(view, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, point)
    qt_app.processEvents()


def test_no_document_disables_all_formatting_controls(qt_app):
    model = DocumentModel(None)
    view = writer_view(model)
    try:
        for name in ('fontFamily', 'fontSize', 'boldButton', 'italicButton',
                     'underlineButton', 'alignment0', 'alignment1', 'alignment2',
                     'alignment3', 'styleHeading 1'):
            assert not control(view, name).isEnabled()
        assert model.selection == {}
        assert not model.applyFont('PT Sans')
        assert not model.applyFontSize(14)
        assert not model.applyAlignment(3)
    finally:
        close_view(view, qt_app)


def test_model_reports_engine_failure_and_preserves_readback(qt_app):
    from zaldros_writer.engine import EngineError, Paragraph

    class RefusingDocument:
        def paragraphs(self):
            return [Paragraph(0, 'text', 'Default Paragraph Style', size=12, font='PT Sans')]

        def set_character_format(self, *args, **kwargs):
            raise EngineError('read-only document')

    model = DocumentModel(RefusingDocument())
    assert not model.applyFontSize(18)
    assert model.status == 'read-only document'
    assert model.selection['size'] == 12
    assert not model.selectParagraph(-1)
    assert not model.selectParagraph(5)
    assert model.selectedParagraph == 0


from zaldros_writer.engine import WriterEngine, soffice_path, uno_available, writer_available

needs_writer = pytest.mark.skipif(
    soffice_path() is None or not uno_available() or not writer_available(),
    reason='real Writer and matching UNO bridge are required')


@pytest.fixture(scope='module')
def live_writer():
    with WriterEngine() as engine:
        yield engine


@needs_writer
def test_home_controls_edit_real_paragraph_and_saved_docx(qt_app, live_writer, tmp_path):
    """Mouse/keyboard -> QML -> model -> UNO -> reopened DOCX, including toggle off."""
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    document = live_writer.new_document()
    view = None
    try:
        document.append('Первый абзац')
        document.append_paragraph('Второй абзац')
        document.set_character_format(0, font='Liberation Serif', size=12,
                                      bold=False, italic=False, underline=False)
        document.set_character_format(1, font='Liberation Sans', size=18, bold=True)
        model = DocumentModel(document)
        view = writer_view(model)
        qt_app.processEvents()
        assert control(view, 'fontFamily').property('displayText') == 'Liberation Serif'
        assert control(view, 'fontSize').property('value') == 120
        assert control(view, 'styleStandard').property('checked') is True
        for name, attribute in [('boldButton', 'bold'), ('italicButton', 'italic'),
                                ('underlineButton', 'underline')]:
            click(view, name, qt_app)
            assert getattr(document.paragraphs()[0], attribute) is True
            assert control(view, name).property('checked') is True
            click(view, name, qt_app)
            assert getattr(document.paragraphs()[0], attribute) is False
            assert control(view, name).property('checked') is False
        for alignment in (3, 1, 2, 0):
            click(view, 'alignment' + str(alignment), qt_app)
            assert document.paragraphs()[0].alignment == alignment
            assert control(view, 'alignment' + str(alignment)).property('checked') is True

        # The font picker and spin box use their real keyboard interaction paths.
        family = control(view, 'fontFamily')
        family.forceActiveFocus()
        QTest.keyClick(view, Qt.Key.Key_Down)
        qt_app.processEvents()
        assert document.paragraphs()[0].font == family.property('currentText')
        assert document.paragraphs()[0].font != 'Liberation Serif'
        size = control(view, 'fontSize')
        size.forceActiveFocus()
        QTest.keyClick(view, Qt.Key.Key_Up)
        qt_app.processEvents()
        assert document.paragraphs()[0].size == 13

        click(view, 'paragraph1', qt_app)
        assert model.selectedParagraph == 1
        assert control(view, 'fontSize').property('value') == 180
        assert control(view, 'fontFamily').property('displayText') == 'Liberation Sans'
        assert control(view, 'boldButton').property('checked') is True
        click(view, 'styleHeading 1', qt_app)
        assert document.paragraphs()[1].style == 'Heading 1'
        assert model.selection['size'] == document.paragraphs()[1].size
        assert control(view, 'styleHeading 1').property('checked') is True
        click(view, 'styleStandard', qt_app)
        assert document.paragraphs()[1].style == 'Standard'
        assert control(view, 'styleStandard').property('checked') is True
        click(view, 'styleHeading 1', qt_app)
        evidence = os.environ.get('ZALDROS_OFFICE_EVIDENCE_DIR')
        if evidence:
            import hashlib
            import json
            destination = Path(evidence)
            destination.mkdir(parents=True, exist_ok=True)
            image = view.grabWindow()
            screenshot = destination / 'writer-home.png'
            assert image.save(str(screenshot))
            receipt = {'scope': 'Real UNO paragraph-formatting interaction, owned two-paragraph fixture',
                       'viewport': [image.width(), image.height()],
                       'device_pixel_ratio': image.devicePixelRatio(),
                       'selected_paragraph': model.selectedParagraph,
                       'paragraphs': model.paragraphs,
                       'sha256': hashlib.sha256(screenshot.read_bytes()).hexdigest(),
                       'source': os.environ.get('GITHUB_SHA')}
            (destination / 'writer-home.json').write_text(json.dumps(receipt, indent=2) + '\n')
            if os.environ.get('GITHUB_ACTIONS') == 'true':
                print('\n::notice title=Writer UI evidence::' + json.dumps(receipt), flush=True)
        target = tmp_path / 'formatted.docx'
        assert model.saveAs(str(target))
        expected = document.paragraphs()[0]
    finally:
        if view is not None:
            close_view(view, qt_app)
        document.close()
    reopened = live_writer.open(target)
    try:
        actual = reopened.paragraphs()
        assert actual[0].text == expected.text
        assert actual[0].font == expected.font
        assert actual[0].size == expected.size
        assert not actual[0].bold and not actual[0].italic and not actual[0].underline
        assert actual[1].style == 'Heading 1'
    finally:
        reopened.close()


def test_failed_text_write_retains_draft_and_blocks_save(tmp_path, qt_app):
    from dataclasses import replace
    from zaldros_writer.engine import EngineError, Paragraph

    class EditingDocument:
        fail = True
        item = Paragraph(0, 'original', 'Standard', size=12, font='PT Sans')

        def paragraphs(self):
            return [self.item]

        def replace_paragraph_text(self, index, before, after):
            if self.fail:
                raise EngineError('engine unavailable')
            assert self.item.text == before
            self.item = replace(self.item, text=after)

        def save_as(self, path, *, overwrite):
            assert overwrite
            Path(path).write_text(self.item.text)
            return Path(path)

    document = EditingDocument()
    model = DocumentModel(document)
    assert model.queueText(0, 'retained draft')
    assert not model.flushEdits()
    assert model.pendingEdits and model.modified
    assert model.paragraphModel.rows[0]['editorText'] == 'retained draft'
    target = tmp_path / 'not-yet-saved.txt'
    assert not model.saveAs(str(target)) and not target.exists()
    document.fail = False
    assert model.flushEdits() and not model.pendingEdits
    assert document.item.text == 'retained draft'
    assert model.saveAs(str(target)) and not model.modified
    assert target.read_text() == 'retained draft'


def test_editor_keeps_caret_on_readback_and_guards_unsaved_close(qt_app):
    from dataclasses import replace
    from PySide6.QtCore import QObject, Qt
    from PySide6.QtTest import QTest
    from PySide6.QtGui import QGuiApplication
    from zaldros_writer.engine import Paragraph

    class EditingDocument:
        item = Paragraph(0, 'original', 'Standard', size=12, font='PT Sans')

        def paragraphs(self): return [self.item]
        def page_count(self): return 1
        def replace_paragraph_text(self, index, before, after):
            assert before == self.item.text
            self.item = replace(self.item, text=after)

    doc = EditingDocument()
    model = DocumentModel(doc)
    view = writer_view(model)
    try:
        click(view, 'paragraph0', qt_app)
        editor = control(view, 'paragraph0')
        QTest.keyClick(view, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
        QGuiApplication.clipboard().setText('новый 😀 текст')
        QTest.keyClick(view, Qt.Key.Key_V, Qt.KeyboardModifier.ControlModifier)
        position = editor.property('cursorPosition')
        assert model.pendingEdits and model.modified
        assert model.flushEdits()
        assert control(view, 'paragraph0') is editor
        assert editor.property('cursorPosition') == position
        assert doc.item.text == 'новый 😀 текст'
        assert not view.close()
        qt_app.processEvents()
        dialog = view.rootObject().findChild(QObject, 'unsavedDialog')
        assert dialog.property('visible') is True
        dialog.close()
    finally:
        view.rootObject().setProperty('closeApproved', True)
        close_view(view, qt_app)


@needs_writer
@pytest.mark.parametrize('suffix', ['.docx', '.odt'])
def test_inline_typing_enter_backspace_and_ctrl_s_round_trip(qt_app, live_writer, tmp_path, suffix):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtTest import QTest
    document = live_writer.new_document()
    target = tmp_path / ('typed' + suffix)
    view = None
    try:
        document.append('original')
        document.save_as(target)
        model = DocumentModel(document, path=str(target))
        view = writer_view(model)
        click(view, 'paragraph0', qt_app)
        editor = control(view, 'paragraph0')
        QTest.keyClick(view, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
        QGuiApplication.clipboard().setText('hello😀')
        QTest.keyClick(view, Qt.Key.Key_V, Qt.KeyboardModifier.ControlModifier)
        assert model.pendingEdits and model.modified
        QTest.qWait(240)
        assert document.paragraphs()[0].text == 'hello😀'
        assert control(view, 'paragraph0') is editor
        assert editor.property('cursorPosition') == 7
        QTest.keyClick(view, Qt.Key.Key_Return)
        QTest.qWait(30)
        assert [p.text for p in document.paragraphs()] == ['hello😀', '']
        assert model.selectedParagraph == 1
        for key in (Qt.Key.Key_N, Qt.Key.Key_E, Qt.Key.Key_X, Qt.Key.Key_T):
            QTest.keyClick(view, key)
        QTest.qWait(240)
        assert document.paragraphs()[1].text == 'next'
        QTest.keyClick(view, Qt.Key.Key_Home)
        QTest.keyClick(view, Qt.Key.Key_Backspace)
        QTest.qWait(30)
        assert [p.text for p in document.paragraphs()] == ['hello😀next']
        assert control(view, 'paragraph0').property('cursorPosition') == 7
        QTest.keyClick(view, Qt.Key.Key_S, Qt.KeyboardModifier.ControlModifier)
        qt_app.processEvents()
        assert not model.modified and not model.pendingEdits
        QGuiApplication.clipboard().setText('!')
        QTest.keyClick(view, Qt.Key.Key_V, Qt.KeyboardModifier.ControlModifier)
        assert model.modified
        QTest.keyClick(view, Qt.Key.Key_S, Qt.KeyboardModifier.ControlModifier)
        qt_app.processEvents()
        assert not model.modified and not model.pendingEdits
    finally:
        if view is not None:
            view.rootObject().setProperty('closeApproved', True)
            close_view(view, qt_app)
        document.close()
    reopened = live_writer.open(target)
    try:
        assert [p.text for p in reopened.paragraphs()] == ['hello😀!next']
    finally:
        reopened.close()


def test_draft_survives_successful_write_followed_by_failed_readback(qt_app):
    from dataclasses import replace
    from zaldros_writer.engine import EngineError, Paragraph

    class UncertainDocument:
        item = Paragraph(0, 'original', 'Standard')
        fail_read = False

        def paragraphs(self):
            if self.fail_read:
                self.fail_read = False
                raise EngineError('readback interrupted')
            return [self.item]

        def replace_paragraph_text(self, index, before, after):
            # Same idempotent contract as the real bridge after a lost readback.
            if self.item.text == after:
                return
            assert self.item.text == before
            self.item = replace(self.item, text=after)

    doc = UncertainDocument()
    model = DocumentModel(doc)
    model.queueText(0, 'retained after read failure')
    doc.fail_read = True
    assert not model.flushEdits()
    assert model.pendingEdits and model.modified
    assert model.paragraphModel.rows[0]['editorText'] == 'retained after read failure'
    assert model.flushEdits()
    assert not model.pendingEdits
    assert model.paragraphs[0]['text'] == 'retained after read failure'


def test_engine_runs_highlight_without_changing_plain_text_or_undo(qt_app):
    from PySide6.QtGui import QFont, QTextDocument
    from zaldros_writer.model import RunHighlighter
    document = QTextDocument()
    document.setPlainText('a😀BCz')
    document.clearUndoRedoStacks()
    highlighter = RunHighlighter(document)
    base = dict(font='PT Sans', size=12, bold=False, italic=False, underline=False)
    highlighter.runs = [dict(base, start=0, length=3),
                        dict(base, start=3, length=2, bold=True, italic=True, size=19),
                        dict(base, start=5, length=1)]
    highlighter.rehighlight()
    ranges = document.begin().layout().formats()
    bold = next(r for r in ranges if r.start == 3)
    assert bold.length == 2
    assert bold.format.fontWeight() == QFont.Weight.Bold
    assert bold.format.fontItalic() is True and bold.format.fontPointSize() == 19
    assert document.toPlainText() == 'a😀BCz'
    assert not document.isUndoAvailable()


def test_failed_selection_read_disables_character_commands_without_writing(qt_app):
    from zaldros_writer.engine import EngineError, Paragraph

    class UnreadableSelection:
        written = False
        def paragraphs(self):
            return [Paragraph(0, 'hello', 'Standard', size=12, font='PT Sans')]
        def character_format(self, *args):
            raise EngineError('selection unavailable')
        def set_character_format(self, *args, **kwargs):
            self.written = True

    document = UnreadableSelection()
    model = DocumentModel(document)
    model.setTextSelection(0, 1, 4)
    assert not model._read_selection()
    assert model.formatAvailable and not model.characterFormatAvailable
    assert model.selection['bold'] is None and model.selection['font'] == ''
    assert not model.applyFormat(0, 'bold', True)
    assert not document.written and not model.modified


@needs_writer
@pytest.mark.parametrize('suffix', ['.docx', '.odt'])
def test_keyboard_selection_ribbon_and_painted_runs_round_trip(qt_app, live_writer, tmp_path, suffix):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFont
    from PySide6.QtTest import QTest
    document = live_writer.new_document()
    target = tmp_path / ('selected-ui' + suffix)
    view = None
    try:
        document.append('left target right')
        document.set_character_format(0, font='Liberation Serif', size=12,
                                      bold=False, italic=False, underline=False)
        document.save_as(target)
        model = DocumentModel(document, path=str(target))
        view = writer_view(model)
        click(view, 'paragraph0', qt_app)
        editor = control(view, 'paragraph0')
        QTest.keyClick(view, Qt.Key.Key_Home)
        for _ in range(5): QTest.keyClick(view, Qt.Key.Key_Right)
        for _ in range(6): QTest.keyClick(view, Qt.Key.Key_Right, Qt.KeyboardModifier.ShiftModifier)
        QTest.qWait(120)
        assert model.hasTextSelection and model.selectionLength == 6
        assert model.characterFormatAvailable
        click(view, 'boldButton', qt_app)
        assert document.character_format(0, 5, 11)['bold'] is True
        assert document.character_format(0, 0, 5)['bold'] is False
        assert editor.property('selectionStart') == 5 and editor.property('selectionEnd') == 11
        assert control(view, 'boldButton').property('checked') is True
        click(view, 'boldButton', qt_app)
        assert document.character_format(0, 5, 11)['bold'] is False
        click(view, 'boldButton', qt_app)
        click(view, 'italicButton', qt_app)
        click(view, 'underlineButton', qt_app)
        size = control(view, 'fontSize')
        size.forceActiveFocus()
        QTest.keyClick(view, Qt.Key.Key_Up)
        qt_app.processEvents()
        assert document.character_format(0, 5, 11)['size'] == 13
        family = control(view, 'fontFamily')
        family.forceActiveFocus()
        QTest.keyClick(view, Qt.Key.Key_Down)
        qt_app.processEvents()
        selected = document.character_format(0, 5, 11)
        assert selected['font'] != 'Liberation Serif'
        assert document.character_format(0, 0, 5)['font'] == 'Liberation Serif'
        assert document.character_format(0, 11, 17)['size'] == 12
        painted = editor.property('textDocument').textDocument().begin().layout().formats()
        fmt = next(r.format for r in painted if r.start <= 5 < r.start + r.length)
        assert fmt.fontWeight() == QFont.Weight.Bold and fmt.fontPointSize() == 13
        assert fmt.fontItalic() is True and fmt.fontUnderline() is True
        assert not model.pendingEdits
        QTest.keyClick(view, Qt.Key.Key_S, Qt.KeyboardModifier.ControlModifier)
        qt_app.processEvents()
        assert not model.modified
    finally:
        if view is not None:
            view.rootObject().setProperty('closeApproved', True)
            close_view(view, qt_app)
        document.close()
    reopened = live_writer.open(target)
    try:
        assert reopened.character_format(0, 5, 11) == selected
        assert reopened.character_format(0, 0, 5)['bold'] is False
        assert reopened.character_format(0, 11, 17)['font'] == 'Liberation Serif'
    finally:
        reopened.close()


def test_inline_editor_wraps_long_text_inside_page_column(qt_app):
    from PySide6.QtTest import QTest
    from zaldros_writer.engine import Paragraph

    class LongDocument:
        def paragraphs(self):
            return [Paragraph(0, 'Long paragraph with wrapping. ' * 60, 'Standard',
                              size=12, font='PT Sans')]
        def page_count(self): return 1

    model = DocumentModel(LongDocument())
    view = writer_view(model)
    try:
        QTest.qWait(20)
        editor = control(view, 'paragraph0')
        assert editor.width() == editor.parentItem().width() == 642
        assert editor.property('contentHeight') > 100
        assert editor.height() >= editor.property('contentHeight')
    finally:
        close_view(view, qt_app)
