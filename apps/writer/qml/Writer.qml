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

Item {
    id: root
    width: 1280
    height: 800

    readonly property var win: ref.window
    readonly property string uiFont: uiFontFamily
    property int activeTab: 1
    property int caretParagraph: 0

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
                text: document.path === "" ? qsTr("Документ1 — Word")
                                           : document.path + " — Word"
                color: "#ffffff"
                font.family: root.uiFont
                font.pixelSize: 13
                anchors.verticalCenter: parent.verticalCenter
            }
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
                        color: index === root.activeTab ? "#185abd" : "#444444"
                        font.family: root.uiFont
                        font.pixelSize: 13
                    }
                    Rectangle {
                        visible: index === root.activeTab
                        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
                        height: 2
                        color: "#185abd"
                    }
                    MouseArea { anchors.fill: parent; onClicked: root.activeTab = index }
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

        Row {
            anchors { left: parent.left; leftMargin: 10; verticalCenter: parent.verticalCenter }
            spacing: 20
            Repeater {
                model: document.groups
                delegate: Column {
                    spacing: 6
                    Row {
                        spacing: 6
                        Repeater {
                            model: modelData.commands
                            delegate: Rectangle {
                                width: Math.max(64, commandLabel.width + 16)
                                height: 56
                                radius: 4
                                color: commandHover.containsMouse ? "#f3f3f3" : "transparent"
                                Text {
                                    id: commandLabel
                                    anchors.centerIn: parent
                                    text: modelData
                                    color: "#333333"
                                    font.family: root.uiFont
                                    font.pixelSize: 12
                                    font.bold: modelData === "Полужирный"
                                    font.italic: modelData === "Курсив"
                                    font.underline: modelData === "Подчёркнутый"
                                }
                                MouseArea {
                                    id: commandHover
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    onClicked: {
                                        var name = modelData;
                                        if (name === "Полужирный")
                                            document.applyFormat(root.caretParagraph, "bold", true);
                                        else if (name === "Курсив")
                                            document.applyFormat(root.caretParagraph, "italic", true);
                                        else if (name === "Подчёркнутый")
                                            document.applyFormat(root.caretParagraph, "underline", true);
                                        else if (name.indexOf("Заголовок") === 0 || name === "Обычный"
                                                 || name === "Цитата")
                                            document.applyStyle(root.caretParagraph, name);
                                    }
                                }
                            }
                        }
                    }
                    Text {
                        text: modelData.title
                        color: "#767676"
                        font.family: root.uiFont
                        font.pixelSize: 11
                        anchors.horizontalCenter: parent.horizontalCenter
                    }
                }
            }
        }
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
            width: 794                       // A4 at 96 dpi — the engine's own default page
            height: Math.max(1123, text.height + 160)
            anchors.horizontalCenter: parent.horizontalCenter
            y: 8
            color: "#ffffff"
            border.width: 1
            border.color: "#d0d0d0"

            Column {
                id: text
                x: 76; y: 76                  // 20 mm margins
                width: page.width - 152
                spacing: 8

                Repeater {
                    model: document.paragraphs
                    delegate: Text {
                        width: text.width
                        wrapMode: Text.WordWrap
                        text: modelData.text
                        color: "#1b1b1b"
                        font.family: root.uiFont
                        font.pixelSize: modelData.style.indexOf("Heading") === 0 ? 22
                                        : (modelData.size > 0 ? modelData.size * 1.33 : 15)
                        font.bold: modelData.bold || modelData.style.indexOf("Heading") === 0
                        font.italic: modelData.italic
                        font.underline: modelData.underline
                        MouseArea {
                            anchors.fill: parent
                            onClicked: root.caretParagraph = modelData.index
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
            text: document.live
                  ? qsTr("Страница %1    Слов: %2").arg(document.pageCount).arg(document.wordCount)
                  : document.status
            color: "#ffffff"
            font.family: root.uiFont
            font.pixelSize: 12
        }
    }
}
