// Zaldros Slides — the window: PowerPoint's shape, Impress's engine.
//
// Left: the slide pane with the deck as the engine reports it. Centre: the current slide, drawn
// from the engine's own placeholder text. Bottom: the speaker notes, which are the engine's notes
// page, not a text file of ours. No slide is invented — an empty deck says why it is empty.

import QtQuick
import QtQuick.Controls

Item {
    id: root
    width: 1280
    height: 800
    readonly property string uiFont: uiFontFamily
    property int activeTab: 1

    Rectangle { anchors.fill: parent; color: "#f0f0f0" }

    Rectangle {
        id: titleBar
        anchors { left: parent.left; right: parent.right; top: parent.top }
        height: 52
        color: "#b7472a"                       // PowerPoint's family of red, our own tone
        Row {
            anchors { left: parent.left; leftMargin: 12; verticalCenter: parent.verticalCenter }
            spacing: 12
            Rectangle {
                width: 22; height: 22; radius: 3; color: "#ffffff"
                anchors.verticalCenter: parent.verticalCenter
                Text { anchors.centerIn: parent; text: "Z"; color: "#b7472a"
                       font.family: root.uiFont; font.pixelSize: 12; font.bold: true }
            }
            Text {
                text: qsTr("Презентация1 — PowerPoint")
                color: "#ffffff"; font.family: root.uiFont; font.pixelSize: 13
                anchors.verticalCenter: parent.verticalCenter
            }
        }
    }

    Rectangle {
        id: tabStrip
        anchors { left: parent.left; right: parent.right; top: titleBar.bottom }
        height: 33
        color: "#f0f0f0"
        Row {
            anchors { left: parent.left; leftMargin: 12; bottom: parent.bottom }
            spacing: 16
            Repeater {
                model: deck.tabs
                delegate: Item {
                    width: tabLabel.width + 14
                    height: tabStrip.height
                    Text {
                        id: tabLabel
                        anchors.centerIn: parent
                        text: modelData
                        color: index === root.activeTab ? "#b7472a" : "#444444"
                        font.family: root.uiFont; font.pixelSize: 13
                    }
                    Rectangle {
                        visible: index === root.activeTab
                        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
                        height: 2; color: "#b7472a"
                    }
                    MouseArea { anchors.fill: parent; onClicked: root.activeTab = index }
                }
            }
        }
    }

    // Ribbon: only commands the engine really performs.
    Rectangle {
        id: ribbon
        anchors { left: parent.left; right: parent.right; top: tabStrip.bottom; margins: 6 }
        anchors.topMargin: 0
        height: 105
        radius: 4
        color: "#ffffff"
        Row {
            anchors { left: parent.left; leftMargin: 12; verticalCenter: parent.verticalCenter }
            spacing: 10
            Repeater {
                model: [{ label: "Создать слайд", action: "add" },
                        { label: "Удалить слайд", action: "remove" },
                        { label: "Макет", action: "layout" },
                        { label: "Переход", action: "transition" }]
                delegate: Rectangle {
                    width: 116; height: 56; radius: 4
                    color: buttonHover.containsMouse ? "#f3f3f3" : "transparent"
                    Text {
                        anchors.centerIn: parent
                        text: modelData.label
                        color: "#333333"; font.family: root.uiFont; font.pixelSize: 12
                    }
                    MouseArea {
                        id: buttonHover
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: {
                            if (modelData.action === "add") deck.addSlide(1);
                            else if (modelData.action === "remove") deck.removeSlide(deck.currentIndex);
                            else if (modelData.action === "layout") layoutMenu.visible = !layoutMenu.visible;
                            else transitionMenu.visible = !transitionMenu.visible;
                        }
                    }
                }
            }
        }
    }

    // The layout and transition pickers show the engine's own lists, not a hand-written menu.
    Rectangle {
        id: layoutMenu
        visible: false
        z: 5
        x: 240; y: ribbon.y + ribbon.height + 2
        width: 260; height: layoutColumn.height + 8
        color: "#ffffff"; border.width: 1; border.color: "#d0d0d0"; radius: 4
        Column {
            id: layoutColumn
            y: 4; width: parent.width
            Repeater {
                model: deck.layouts
                delegate: Rectangle {
                    width: layoutMenu.width; height: 30
                    color: layoutHover.containsMouse ? "#f3f3f3" : "transparent"
                    Text { x: 12; anchors.verticalCenter: parent.verticalCenter
                           text: modelData.title; color: "#333333"
                           font.family: root.uiFont; font.pixelSize: 12 }
                    MouseArea {
                        id: layoutHover
                        anchors.fill: parent; hoverEnabled: true
                        onClicked: { deck.setLayout(deck.currentIndex, modelData.id);
                                     layoutMenu.visible = false }
                    }
                }
            }
        }
    }
    Rectangle {
        id: transitionMenu
        visible: false
        z: 5
        x: 360; y: ribbon.y + ribbon.height + 2
        width: 220; height: transitionColumn.height + 8
        color: "#ffffff"; border.width: 1; border.color: "#d0d0d0"; radius: 4
        Column {
            id: transitionColumn
            y: 4; width: parent.width
            Repeater {
                model: deck.transitions
                delegate: Rectangle {
                    width: transitionMenu.width; height: 30
                    color: transitionHover.containsMouse ? "#f3f3f3" : "transparent"
                    Text { x: 12; anchors.verticalCenter: parent.verticalCenter
                           text: modelData.title; color: "#333333"
                           font.family: root.uiFont; font.pixelSize: 12 }
                    MouseArea {
                        id: transitionHover
                        anchors.fill: parent; hoverEnabled: true
                        onClicked: { deck.setTransition(deck.currentIndex, modelData.id);
                                     transitionMenu.visible = false }
                    }
                }
            }
        }
    }

    // --- slide pane ------------------------------------------------------------------------
    Rectangle {
        id: pane
        anchors { left: parent.left; top: ribbon.bottom; bottom: statusBar.top; margins: 8 }
        width: 220
        color: "#ffffff"
        border.width: 1; border.color: "#e0e0e0"

        ListView {
            objectName: "slidePane"
            anchors.fill: parent
            anchors.margins: 6
            clip: true
            spacing: 8
            model: deck.slides
            delegate: Row {
                spacing: 6
                Text {
                    text: (modelData.index + 1)
                    color: "#767676"; font.family: root.uiFont; font.pixelSize: 11
                    anchors.verticalCenter: parent.verticalCenter
                }
                Rectangle {
                    width: 170; height: 96
                    color: "#ffffff"
                    border.width: modelData.index === deck.currentIndex ? 2 : 1
                    border.color: modelData.index === deck.currentIndex ? "#b7472a" : "#d0d0d0"
                    Column {
                        anchors { fill: parent; margins: 6 }
                        spacing: 3
                        Text {
                            width: parent.width; elide: Text.ElideRight
                            text: modelData.title
                            color: "#1b1b1b"; font.family: root.uiFont
                            font.pixelSize: 10; font.bold: true
                        }
                        Text {
                            width: parent.width; wrapMode: Text.WordWrap; maximumLineCount: 4
                            elide: Text.ElideRight
                            text: modelData.body
                            color: "#555555"; font.family: root.uiFont; font.pixelSize: 8
                        }
                    }
                    MouseArea { anchors.fill: parent; onClicked: deck.select(modelData.index) }
                }
            }
        }
    }

    // --- current slide ---------------------------------------------------------------------
    Rectangle {
        anchors { left: pane.right; right: parent.right; top: ribbon.bottom
                  bottom: notes.top; margins: 12 }
        color: "#ffffff"
        border.width: 1; border.color: "#d0d0d0"

        Column {
            anchors { fill: parent; margins: 40 }
            spacing: 18
            Text {
                width: parent.width; wrapMode: Text.WordWrap
                text: deck.live ? deck.current.title : ""
                color: "#1b1b1b"; font.family: root.uiFont; font.pixelSize: 32
            }
            Text {
                width: parent.width; wrapMode: Text.WordWrap
                text: deck.live ? deck.current.body : deck.status
                color: deck.live ? "#333333" : "#767676"
                font.family: root.uiFont; font.pixelSize: deck.live ? 18 : 13
            }
        }
    }

    // --- notes ------------------------------------------------------------------------------
    Rectangle {
        id: notes
        anchors { left: pane.right; right: parent.right; bottom: statusBar.top; margins: 12 }
        height: 92
        color: "#ffffff"
        border.width: 1; border.color: "#e0e0e0"
        Text {
            x: 10; y: 6
            text: qsTr("Заметки к слайду")
            color: "#767676"; font.family: root.uiFont; font.pixelSize: 11
        }
        TextInput {
            objectName: "notesEditor"
            anchors { fill: parent; topMargin: 26; leftMargin: 10; rightMargin: 10 }
            text: deck.live ? deck.current.notes : ""
            color: "#333333"; font.family: root.uiFont; font.pixelSize: 13
            clip: true
            onAccepted: deck.setNotes(deck.currentIndex, text)
        }
    }

    Rectangle {
        id: statusBar
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
        height: 24
        color: "#b7472a"
        Text {
            anchors { left: parent.left; leftMargin: 12; verticalCenter: parent.verticalCenter }
            text: deck.live
                  ? qsTr("Слайд %1 из %2    Макет: %3").arg(deck.currentIndex + 1)
                        .arg(deck.slides.length).arg(deck.current.layoutName)
                  : deck.status
            color: "#ffffff"; font.family: root.uiFont; font.pixelSize: 12
        }
    }
}
