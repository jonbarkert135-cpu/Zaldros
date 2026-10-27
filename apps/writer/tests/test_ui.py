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
