// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Controls

Flickable {
    id: ribbon
    required property var model
    required property string uiFont
    readonly property bool ready: model.formatAvailable
    readonly property var selection: model.selection
    contentWidth: groups.width + 20
    clip: true
    flickableDirection: Flickable.HorizontalFlick
    ScrollBar.horizontal: ScrollBar { }
    Row {
        id: groups
        x: 10; y: 6; spacing: 12
        Column {
            width: 290; spacing: 4
            Row {
                spacing: 6
                ComboBox {
                    id: fontFamily
                    objectName: "fontFamily"
                    width: 196; height: 30
                    enabled: ribbon.ready
                    font.family: ribbon.uiFont
                    model: ribbon.model.fontFamilies
                    currentIndex: ribbon.ready ? find(ribbon.selection.font) : -1
                    displayText: ribbon.ready ? ribbon.selection.font : ""
                    Accessible.name: qsTr("Шрифт")
                    onActivated: ribbon.model.applyFont(currentText)
                }
                SpinBox {
                    id: fontSize
                    objectName: "fontSize"
                    width: 88; height: 30
                    enabled: ribbon.ready
                    font.family: ribbon.uiFont
                    editable: true
                    from: 10; to: 4000; stepSize: 10
                    value: ribbon.ready && ribbon.selection.size > 0 ? Math.round(ribbon.selection.size * 10) : 10
                    Accessible.name: qsTr("Размер шрифта")
                    textFromValue: function(value, locale) {
                        if (!ribbon.ready || ribbon.selection.size === 0) return "—";
                        return Number(value / 10).toLocaleString(locale, 'f', value % 10 === 0 ? 0 : 1);
                    }
                    valueFromText: function(text, locale) { return Math.round(Number.fromLocaleString(locale, text) * 10); }
                    validator: DoubleValidator { bottom: 1; top: 400; decimals: 1; locale: fontSize.locale.name }
                    onValueModified: ribbon.model.applyFontSize(value / 10)
                }
            }
            Row {
                spacing: 4
                Repeater {
                    model: [
                        {key: "bold", label: qsTr("Ж"), title: qsTr("Полужирный")},
                        {key: "italic", label: qsTr("К"), title: qsTr("Курсив")},
                        {key: "underline", label: qsTr("Ч"), title: qsTr("Подчёркнутый")}
                    ]
                    delegate: Button {
                        required property var modelData
                        objectName: modelData.key + "Button"
                        width: 34; height: 30
                        enabled: ribbon.ready
                        text: modelData.label
                        checked: ribbon.ready && ribbon.selection[modelData.key] === true
                        highlighted: checked
                        font.bold: modelData.key === "bold"
                        font.family: ribbon.uiFont
                        font.italic: modelData.key === "italic"
                        font.underline: modelData.key === "underline"
                        Accessible.name: modelData.title
                        ToolTip.visible: hovered
                        ToolTip.text: modelData.title
                        onClicked: ribbon.model.applyFormat(ribbon.model.selectedParagraph, modelData.key, !checked)
                    }
                }
            }
            Label { text: qsTr("Шрифт"); color: "#666666"; font.pixelSize: 11; anchors.horizontalCenter: parent.horizontalCenter }
        }
        Rectangle { width: 1; height: 86; color: "#dddddd" }
        Column {
            width: 170; spacing: 4
            Label { text: qsTr("Выравнивание"); height: 30; verticalAlignment: Text.AlignVCenter; font.pixelSize: 12 }
            Row {
                spacing: 4
                Repeater {
                    model: [
                        {code: 0, title: qsTr("По левому краю")},
                        {code: 3, title: qsTr("По центру")},
                        {code: 1, title: qsTr("По правому краю")},
                        {code: 2, title: qsTr("По ширине")}
                    ]
                    delegate: Button {
                        id: alignmentButton
                        required property var modelData
                        objectName: "alignment" + modelData.code
                        width: 36; height: 30
                        enabled: ribbon.ready
                        checked: ribbon.ready && ribbon.selection.alignment === modelData.code
                        highlighted: checked
                        Accessible.name: modelData.title
                        ToolTip.visible: hovered
                        ToolTip.text: modelData.title
                        contentItem: Item {
                            Repeater {
                                model: 4
                                Rectangle {
                                    required property int index
                                    width: alignmentButton.modelData.code === 2 || index % 2 === 0 ? 20 : 13
                                    height: 2; y: 2 + index * 5
                                    x: alignmentButton.modelData.code === 3 ? (parent.width - width) / 2
                                       : alignmentButton.modelData.code === 1 ? parent.width - width : 0
                                    color: alignmentButton.enabled ? "#444444" : "#aaaaaa"
                                }
                            }
                        }
                        onClicked: ribbon.model.applyAlignment(modelData.code)
                    }
                }
            }
            Label { text: qsTr("Абзац"); color: "#666666"; font.pixelSize: 11; anchors.horizontalCenter: parent.horizontalCenter }
        }
        Rectangle { width: 1; height: 86; color: "#dddddd" }
        Column {
            spacing: 4
            Row {
                spacing: 4
                Repeater {
                    model: [
                        {key: "Standard", label: qsTr("Обычный"), sample: qsTr("Обычный текст"), size: 15},
                        {key: "Heading 1", label: qsTr("Заголовок 1"), sample: qsTr("Заголовок"), size: 20},
                        {key: "Heading 2", label: qsTr("Заголовок 2"), sample: qsTr("Подзаголовок"), size: 17},
                        {key: "Quotations", label: qsTr("Цитата"), sample: qsTr("Цитата"), size: 15}
                    ]
                    delegate: Button {
                        id: styleButton
                        required property var modelData
                        objectName: "style" + modelData.key
                        width: 116; height: 64
                        enabled: ribbon.ready
                        checked: ribbon.ready && ribbon.selection.style === modelData.key
                        highlighted: checked
                        Accessible.name: modelData.label
                        contentItem: Column {
                            spacing: 7
                            Text { width: parent.width; elide: Text.ElideRight; text: styleButton.modelData.sample; font.family: ribbon.uiFont; font.pixelSize: styleButton.modelData.size; color: styleButton.enabled ? "#244b78" : "#aaaaaa" }
                            Text { width: parent.width; elide: Text.ElideRight; text: styleButton.modelData.label; font.family: ribbon.uiFont; font.pixelSize: 11; color: "#666666" }
                        }
                        onClicked: ribbon.model.applyStyle(ribbon.model.selectedParagraph, modelData.key)
                    }
                }
            }
            Label { text: qsTr("Стили"); color: "#666666"; font.pixelSize: 11; anchors.horizontalCenter: parent.horizontalCenter }
        }
    }
}
