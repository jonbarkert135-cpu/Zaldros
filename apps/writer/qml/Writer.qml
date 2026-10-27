// SPDX-License-Identifier: GPL-3.0-or-later
// Zaldros Writer — the window.
//
// Sizes come from ref.window, which is system/theme/word-reference.json. That file is DERIVED
// from the measured Excel capture (Word and Excel share one Office ribbon after the 2023
// refresh) and says so in its own header: derived, not measured. Nothing Microsoft-owned is
// embedded — the letters B / I / U are letters.
//
// The page shows what the engine reports. With no engine there are no paragraphs and the status
// bar carries the reason, which is the honest state of a word processor with no engine.

import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs

Item {
    id: root
    width: 1280
    height: 800

    readonly property var win: ref.window
    readonly property string uiFont: uiFontFamily
    property int activeTab: 1

    Rectangle { anchors.fill: parent; color: "#f0f0f0" }

    // ---------------------------------------------------------------- title bar
    Rectangle {
        id: titleBar
        anchors { left: parent.left; right: parent.right; top: parent.top }
        height: win.title_bar_height
        color: "#185abd"                     // Word's own blue family, our own tone

        Row {
            anchors { left: parent.left; leftMargin: 12; verticalCenter: parent.verticalCenter }
            spacing: 14
            Rectangle {
                width: 22; height: 22; radius: 3; color: "#ffffff"
                anchors.verticalCenter: parent.verticalCenter
                Rectangle { anchors.centerIn: parent; width: 14; height: 14; radius: 2
                            color: "#185abd" }
                Text { anchors.centerIn: parent; text: "Z"; color: "#ffffff"
                       font.family: root.uiFont; font.pixelSize: 11; font.bold: true }
            }
            Text {
                text: (document.modified ? "* " : "") + (document.path === "" ? qsTr("Документ1 — Zaldros Writer")
                                           : document.path + " — Zaldros Writer")
                width: titleBar.width - 240
                elide: Text.ElideMiddle
                color: "#ffffff"
                font.family: root.uiFont
                font.pixelSize: 13
                anchors.verticalCenter: parent.verticalCenter
            }
        }
    }

    property bool closeApproved: false
    property bool closeAfterSave: false

    function saved(ok) {
        if (ok && closeAfterSave) {
            closeApproved = true;
            root.Window.window.close();
        }
        closeAfterSave = false;
    }
    function saveDocument() {
        if (!document.live) return;
        if (document.path === "") saveDialog.open();
        else saved(document.saveAs(document.path));
    }
    Button {
        objectName: "saveButton"
        anchors { right: parent.right; rightMargin: 12; top: parent.top; topMargin: 10 }
        text: qsTr("Сохранить")
        enabled: document.live
        onClicked: root.saveDocument()
    }
    Shortcut { sequences: [StandardKey.Save]; onActivated: root.saveDocument() }
    Shortcut { sequences: [StandardKey.SaveAs]; onActivated: if (document.live) saveDialog.open() }
    FileDialog {
        id: saveDialog
        title: qsTr("Сохранить документ")
        fileMode: FileDialog.SaveFile
        defaultSuffix: selectedNameFilter.index === 1 ? "odt" : "docx"
        nameFilters: [qsTr("Документ Word (*.docx)"), qsTr("Текст OpenDocument (*.odt)")]
        onAccepted: root.saved(document.saveAsUrl(selectedFile))
        onRejected: root.closeAfterSave = false
    }
    Connections {
        target: root.Window.window
        function onClosing(event) {
            if (!root.closeApproved && document.modified) {
                event.accepted = false;
                closeDialog.open();
            }
        }
    }
    Dialog {
        id: closeDialog
        objectName: "unsavedDialog"
        width: 440
        anchors.centerIn: parent
        modal: true
        title: qsTr("Сохранить изменения?")
        contentItem: Label { text: qsTr("Документ содержит несохранённые изменения.") }
        footer: Row {
            spacing: 8; padding: 12
            Button { text: qsTr("Сохранить"); onClicked: { closeDialog.close(); root.closeAfterSave = true; root.saveDocument(); } }
            Button { text: qsTr("Не сохранять"); onClicked: { root.closeApproved = true; closeDialog.close(); root.Window.window.close(); } }
            Button { objectName: "cancelClose"; text: qsTr("Отмена"); onClicked: closeDialog.close() }
        }
    }
    Connections {
        target: document
        function onFocusRequested(index, position) {
            Qt.callLater(function() {
                var editor = paragraphRepeater.itemAt(index);
                if (editor) { editor.forceActiveFocus(); editor.cursorPosition = position; }
            });
        }
    }

    // ---------------------------------------------------------------- ribbon tabs
    Rectangle {
        id: tabStrip
        anchors { left: parent.left; right: parent.right; top: titleBar.bottom }
        height: win.tab_strip_height
        color: "#f0f0f0"

        Row {
            anchors { left: parent.left; leftMargin: 12; bottom: parent.bottom }
            spacing: 18
            Repeater {
                model: document.tabs
                delegate: Item {
                    width: label.width + 16
                    height: tabStrip.height
                    Text {
                        id: label
                        anchors.centerIn: parent
                        text: modelData
                        color: index === root.activeTab ? "#185abd" : "#888888"
                        font.family: root.uiFont
                        font.pixelSize: 13
                    }
                    Rectangle {
                        visible: index === root.activeTab
                        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
                        height: 2
                        color: "#185abd"
                    }
                    HoverHandler { id: tabHover }
                    ToolTip.visible: tabHover.hovered && index !== 1
                    ToolTip.text: qsTr("Этот раздел пока недоступен")
                }
            }
        }
    }

    // ---------------------------------------------------------------- ribbon body
    Rectangle {
        id: ribbon
        anchors { left: parent.left; right: parent.right; top: tabStrip.bottom; margins: 6 }
        anchors.topMargin: 0
        height: win.ribbon_body_height
        radius: win.ribbon_card_radius
        color: "#ffffff"

        HomeRibbon { anchors.fill: parent; model: document; uiFont: root.uiFont }
    }

    // ---------------------------------------------------------------- page
    Flickable {
        id: canvas
        anchors { left: parent.left; right: parent.right; top: ribbon.bottom; bottom: statusBar.top }
        anchors.margins: 16
        contentHeight: page.height + 32
        clip: true

        Rectangle {
            id: page
            width: 794                       // Approximate preview frame, not engine page geometry
            height: Math.max(1123, text.height + 160)
            anchors.horizontalCenter: parent.horizontalCenter
            y: 8
            color: "#ffffff"
            border.width: 1
            border.color: "#d0d0d0"

            Column {
                id: text
                x: 76; y: 76                  // Fixed preview padding
                width: page.width - 152
                spacing: 8

                Repeater {
                    id: paragraphRepeater
                    model: document.paragraphModel
                    delegate: TextArea {
                        id: editor
                        required property var paragraph
                        objectName: "paragraph" + paragraph.index
                        width: parent.width
                        height: Math.max(28, contentHeight + topPadding + bottomPadding)
                        wrapMode: TextEdit.Wrap
                        textFormat: TextEdit.PlainText
                        selectByMouse: true
                        persistentSelection: true
                        leftPadding: 0; rightPadding: 0; topPadding: 2; bottomPadding: 2
                        text: paragraph.editorText
                        color: "#1b1b1b"
                        background: Rectangle { color: document.selectedParagraph === editor.paragraph.index ? "#edf4fc" : "transparent" }
                        font.family: paragraph.font || root.uiFont
                        font.pointSize: paragraph.size > 0 ? paragraph.size : 11
                        horizontalAlignment: paragraph.alignment === 3 ? Text.AlignHCenter
                                             : paragraph.alignment === 1 ? Text.AlignRight
                                             : paragraph.alignment === 2 ? Text.AlignJustify : Text.AlignLeft
                        font.bold: paragraph.bold === true
                        font.italic: paragraph.italic === true
                        font.underline: paragraph.underline === true
                        Accessible.name: qsTr("Абзац %1").arg(paragraph.index + 1)
                        function reportSelection() {
                            if (activeFocus) document.setTextSelection(paragraph.index, selectionStart, selectionEnd);
                        }
                        Component.onCompleted: document.attachEditor(paragraph.index, textDocument)
                        onActiveFocusChanged: if (activeFocus && document.selectParagraph(paragraph.index)) reportSelection()
                        onSelectionStartChanged: reportSelection()
                        onSelectionEndChanged: reportSelection()
                        onTextChanged: if (activeFocus && text !== paragraph.editorText) document.queueText(paragraph.index, text)
                        Keys.onReturnPressed: function(event) {
                            if (selectionStart !== selectionEnd) remove(selectionStart, selectionEnd);
                            document.splitParagraph(paragraph.index, cursorPosition);
                            event.accepted = true;
                        }
                        Keys.onEnterPressed: function(event) {
                            if (selectionStart !== selectionEnd) remove(selectionStart, selectionEnd);
                            document.splitParagraph(paragraph.index, cursorPosition);
                            event.accepted = true;
                        }
                        Keys.onPressed: function(event) {
                            if (event.key === Qt.Key_Backspace && cursorPosition === 0
                                    && selectionStart === selectionEnd && paragraph.index > 0) {
                                document.mergeParagraph(paragraph.index); event.accepted = true;
                            } else if (event.key === Qt.Key_Delete && cursorPosition === length
                                    && selectionStart === selectionEnd && paragraph.index + 1 < document.paragraphs.length) {
                                document.mergeParagraph(paragraph.index + 1); event.accepted = true;
                            } else event.accepted = false;
                        }

                    }
                }

                Text {
                    visible: document.paragraphs.length === 0
                    text: document.status
                    color: "#767676"
                    font.family: root.uiFont
                    font.pixelSize: 13
                }
            }
        }
    }

    // ---------------------------------------------------------------- status bar
    Rectangle {
        id: statusBar
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
        height: 24
        color: "#185abd"

        Text {
            anchors { left: parent.left; leftMargin: 12; verticalCenter: parent.verticalCenter }
            width: parent.width - selectionStatus.width - 36
            elide: Text.ElideRight
            text: document.status || (document.live
                  ? qsTr("Страниц: %1    Слов: %2").arg(document.pageCount).arg(document.wordCount)
                  : "")
            color: "#ffffff"
            font.family: root.uiFont
            font.pixelSize: 12
        }
        Text {
            id: selectionStatus
            anchors { right: parent.right; rightMargin: 12; verticalCenter: parent.verticalCenter }
            text: document.formatAvailable ? (document.pendingEdits ? qsTr("Текст ожидает записи — ") : "") + (document.hasTextSelection ? qsTr("Шрифт — к выделению; стиль — к абзацу") : qsTr("Абзац %1 — форматирование всего абзаца").arg(document.selectedParagraph + 1)) : ""
            color: "#ffffff"; font.family: root.uiFont; font.pixelSize: 12
        }
    }
}
