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
                text: document.path === "" ? qsTr("Документ1 — Zaldros Writer")
                                           : document.path + " — Zaldros Writer"
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
                    delegate: Rectangle {
                        objectName: "paragraph" + modelData.index
                        width: text.width
                        height: Math.max(24, paragraphText.implicitHeight)
                        color: document.selectedParagraph === modelData.index ? "#edf4fc" : "transparent"
                        Text {
                        id: paragraphText
                        width: parent.width
                        wrapMode: Text.WordWrap
                        text: modelData.text
                        color: "#1b1b1b"
                        font.family: modelData.font || root.uiFont
                        font.pointSize: modelData.size > 0 ? modelData.size : 11
                        horizontalAlignment: modelData.alignment === 3 ? Text.AlignHCenter
                                             : modelData.alignment === 1 ? Text.AlignRight
                                             : modelData.alignment === 2 ? Text.AlignJustify : Text.AlignLeft
                        font.bold: modelData.bold === true
                        font.italic: modelData.italic === true
                        font.underline: modelData.underline === true
                        }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: document.selectParagraph(modelData.index)
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
            text: document.formatAvailable ? qsTr("Абзац %1 — форматирование всего абзаца").arg(document.selectedParagraph + 1) : ""
            color: "#ffffff"; font.family: root.uiFont; font.pixelSize: 12
        }
    }
}
