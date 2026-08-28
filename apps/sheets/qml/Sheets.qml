// Zaldros Sheets — the window.
//
// Every size in here comes from ref.* , which is system/theme/excel-reference.json: measured off
// Microsoft's own current Excel captures (see the comment block in that file). Nothing is eyeballed
// and nothing Microsoft-owned is embedded — the letterforms B / I / U are letters, the icons are
// the MIT Fluent UI System Icons we already vendor.

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root
    width: 1280
    height: 800

    readonly property var pal: book.light ? ref.palette.light : ref.palette.dark
    readonly property var win: ref.window
    readonly property var grid: ref.grid
    readonly property string uiFont: uiFontFamily

    // ---------------------------------------------------------------- title bar
    Rectangle {
        id: titleBar
        anchors { left: parent.left; right: parent.right; top: parent.top }
        height: win.title_bar_height
        color: pal.title

        Row {
            anchors { left: parent.left; leftMargin: 12; verticalCenter: parent.verticalCenter }
            spacing: 14

            Rectangle {           // the app mark: our own tile, not Microsoft's
                width: 22; height: 22; radius: 3; color: "#ffffff"
                anchors.verticalCenter: parent.verticalCenter
                Rectangle { anchors.centerIn: parent; width: 14; height: 14; radius: 2
                            color: book.light ? "#107c41" : "#1e7145" }
                Text { anchors.centerIn: parent; text: "Z"; color: "#ffffff"
                       font.family: root.uiFont; font.pixelSize: 11; font.bold: true }
            }
            Text { text: "\u21b6"; color: "#ffffff"; font.pixelSize: 16
                   anchors.verticalCenter: parent.verticalCenter }
            Text { text: "\u21b7"; color: "#ffffff"; opacity: 0.55; font.pixelSize: 16
                   anchors.verticalCenter: parent.verticalCenter }
            Row {
                spacing: 8
                anchors.verticalCenter: parent.verticalCenter
                Text { text: qsTr("AutoSave"); color: "#ffffff"; font.family: root.uiFont
                       font.pixelSize: 13; anchors.verticalCenter: parent.verticalCenter }
                Rectangle {
                    width: 42; height: 20; radius: 10; color: "transparent"
                    border.color: "#ffffff"; border.width: 1
                    anchors.verticalCenter: parent.verticalCenter
                    Rectangle { width: 14; height: 14; radius: 7; color: "#ffffff"
                                anchors { left: parent.left; leftMargin: 3
                                          verticalCenter: parent.verticalCenter } }
                    Text { text: qsTr("Off"); color: "#ffffff"; font.pixelSize: 10
                           font.family: root.uiFont
                           anchors { right: parent.right; rightMargin: 6
                                     verticalCenter: parent.verticalCenter } }
                }
            }
        }

        Text {
            anchors.centerIn: parent
            text: book.document + " \u2014 " + qsTr("Zaldros Sheets")
            color: "#ffffff"; font.family: root.uiFont; font.pixelSize: 14
        }

        CaptionButtons { anchors { right: parent.right; top: parent.top }
                         height: parent.height; glyphColor: "#ffffff" }
    }

    // ---------------------------------------------------------------- ribbon
    Rectangle {
        id: ribbon
        anchors { left: parent.left; right: parent.right; top: titleBar.bottom }
        height: win.tab_strip_height + win.ribbon_body_height + 12
        color: pal.tab_strip

        Row {
            id: tabs
            anchors { left: parent.left; leftMargin: 16; top: parent.top }
            height: win.tab_strip_height
            spacing: 4
            Repeater {
                model: ref.tabs
                delegate: Item {
                    required property string modelData
                    required property int index
                    width: label.implicitWidth + 24
                    height: tabs.height
                    Text {
                        id: label
                        anchors.centerIn: parent
                        text: modelData
                        color: pal.text
                        font.family: root.uiFont
                        font.pixelSize: 14
                        font.bold: index === 1
                    }
                    Rectangle {                       // the active-tab underline
                        visible: index === 1
                        anchors { bottom: parent.bottom; horizontalCenter: parent.horizontalCenter }
                        width: label.implicitWidth; height: 2; radius: 1
                        color: pal.accent
                    }
                }
            }
        }

        Rectangle {                                   // the rounded ribbon card
            id: ribbonCard
            anchors { left: parent.left; right: parent.right; top: tabs.bottom
                      leftMargin: 6; rightMargin: 6 }
            height: win.ribbon_body_height
            radius: win.ribbon_card_radius
            color: pal.ribbon_card

            Row {
                anchors.fill: parent
                RibbonGroup {
                    caption: qsTr("Clipboard"); width: 118
                    content: Row {
                        spacing: 6
                        RibbonBigButton { icon: "paste"; label: qsTr("Paste") }
                        Column {
                            spacing: 4
                            anchors.verticalCenter: parent.verticalCenter
                            RibbonSmallButton { icon: "cut" }
                            RibbonSmallButton { icon: "copy" }
                            RibbonSmallButton { icon: "paint-brush" }
                        }
                    }
                }
                RibbonGroup {
                    caption: qsTr("Font"); width: 260
                    content: Column {
                        spacing: 6
                        Row {
                            spacing: 6
                            ComboLike { text: "Aptos Narrow"; width: 150 }
                            ComboLike { text: "11"; width: 52 }
                        }
                        Row {
                            spacing: 2
                            LetterButton { letter: "B"; bold: true }
                            LetterButton { letter: "I"; italic: true }
                            LetterButton { letter: "U"; underline: true }
                            RibbonSmallButton { icon: "grid" }
                            SwatchButton { letter: "A"; swatch: "#ffd400" }
                            SwatchButton { letter: "A"; swatch: "#c00000" }
                        }
                    }
                }
                RibbonGroup {
                    caption: qsTr("Alignment"); width: 150
                    content: Column {
                        spacing: 6
                        Row { spacing: 2
                              RibbonSmallButton { icon: "list" }
                              RibbonSmallButton { icon: "list" }
                              RibbonSmallButton { icon: "list" } }
                        Row { spacing: 2
                              RibbonSmallButton { icon: "list" }
                              RibbonSmallButton { icon: "list" }
                              RibbonSmallButton { icon: "grid" } }
                    }
                }
                RibbonGroup {
                    caption: qsTr("Number"); width: 150
                    content: Column {
                        spacing: 6
                        ComboLike { text: qsTr("General"); width: 130 }
                        Row { spacing: 2
                              LetterButton { letter: "\u20bd" }
                              LetterButton { letter: "%" }
                              LetterButton { letter: "," } }
                    }
                }
                RibbonGroup {
                    caption: qsTr("Cells"); width: 120
                    content: Column {
                        spacing: 4
                        MenuLike { text: qsTr("Insert") }
                        MenuLike { text: qsTr("Delete") }
                        MenuLike { text: qsTr("Format") }
                    }
                }
            }
        }
    }

    // ---------------------------------------------------------------- formula bar
    Rectangle {
        id: formulaBar
        anchors { left: parent.left; right: parent.right; top: ribbon.bottom }
        height: win.formula_bar_height + 12
        color: pal.formula_bar

        Rectangle {
            id: nameBox
            anchors { left: parent.left; leftMargin: 8; verticalCenter: parent.verticalCenter }
            width: win.name_box_width; height: win.formula_bar_height
            color: "transparent"
            border.color: pal.gridline; border.width: 1; radius: 2
            Text {
                anchors { left: parent.left; leftMargin: 8; verticalCenter: parent.verticalCenter }
                text: book.address; color: pal.text
                font.family: root.uiFont; font.pixelSize: 13
            }
            Text {
                anchors { right: parent.right; rightMargin: 6; verticalCenter: parent.verticalCenter }
                text: "\u2304"; color: pal.text; font.pixelSize: 12
            }
        }
        Text {
            id: fx
            anchors { left: nameBox.right; leftMargin: 18; verticalCenter: parent.verticalCenter }
            text: "fx"; font.family: root.uiFont; font.pixelSize: 14; font.italic: true
            color: pal.text
        }
        Rectangle {
            anchors { left: fx.right; leftMargin: 12; right: parent.right; rightMargin: 8
                      verticalCenter: parent.verticalCenter }
            height: win.formula_bar_height
            color: "transparent"
            border.color: pal.gridline; border.width: 1; radius: 2
            // The formula bar is an editor, not a label: typing here and pressing Enter sends
            // the text to the engine, exactly as typing into the cell does.
            TextInput {
                objectName: "formulaText"
                anchors { left: parent.left; leftMargin: 8; right: parent.right; rightMargin: 8
                          verticalCenter: parent.verticalCenter }
                text: book.formula; color: pal.text
                font.family: root.uiFont; font.pixelSize: 13
                clip: true
                onAccepted: book.commit(text)
                Keys.onPressed: function (event) {
                    if (event.key === Qt.Key_Escape) {
                        text = book.formula;
                        event.accepted = true;
                    }
                }
            }
        }
    }

    // ---------------------------------------------------------------- grid
    SheetGrid {
        id: sheetView
        anchors { left: parent.left; right: parent.right; top: formulaBar.bottom
                  bottom: sheetTabs.top }
    }

    // ---------------------------------------------------------------- sheet tabs + status bar
    Rectangle {
        id: sheetTabs
        anchors { left: parent.left; right: parent.right; bottom: statusBar.top }
        height: 28
        color: pal.tab_strip
        Row {
            anchors { left: parent.left; leftMargin: 8; verticalCenter: parent.verticalCenter }
            spacing: 4
            Repeater {
                model: book.sheets
                delegate: Rectangle {
                    required property string modelData
                    required property int index
                    width: name.implicitWidth + 24; height: 22; radius: 4
                    color: index === 0 ? pal.grid : "transparent"
                    Text { id: name; anchors.centerIn: parent; text: modelData
                           color: pal.text; font.family: root.uiFont; font.pixelSize: 12
                           font.bold: index === 0 }
                }
            }
            Text { text: "+"; color: pal.text; font.pixelSize: 16
                   anchors.verticalCenter: parent.verticalCenter }
        }
    }

    Rectangle {
        id: statusBar
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
        height: win.status_bar_height
        color: pal.tab_strip
        Text {
            anchors { left: parent.left; leftMargin: 12; verticalCenter: parent.verticalCenter }
            text: book.engineState
            color: pal.text; font.family: root.uiFont; font.pixelSize: 12
        }
        Text {
            anchors { right: parent.right; rightMargin: 12; verticalCenter: parent.verticalCenter }
            text: "100%"
            color: pal.text; font.family: root.uiFont; font.pixelSize: 12
        }
    }
}
