import QtQuick
import ZaldrosTheme

// A Zaldros-decorated application window: 8 px rounded corners, 32 px title bar, Windows-order
// minimise / maximise / close buttons with the red close hover, and distinct active/inactive states.
// This is the decoration *design*; on the real system KWin draws it (ADR-0002).
Item {
    id: win
    property string title: "Окно"
    property bool active: true
    property alias content: body.data

    Rectangle {
        anchors.fill: parent
        anchors.margins: -1
        radius: Theme.radiusMedium + 1
        color: Theme.shadow
        opacity: win.active ? 0.55 : 0.25
        z: -1
    }

    Rectangle {
        anchors.fill: parent
        radius: Theme.radiusMedium
        color: Theme.background
        border.width: 1
        border.color: win.active ? Theme.borderStrong : Theme.border
        clip: true

        Rectangle {
            id: titleBar
            width: parent.width
            height: 32
            color: win.active ? Theme.surfaceElevated : Theme.surface

            Text {
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                anchors.leftMargin: 12
                text: win.title
                color: win.active ? Theme.textPrimary : Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontCaption + 1
            }

            Row {
                anchors.right: parent.right
                anchors.top: parent.top
                Repeater {
                    model: [{ g: "minimize" }, { g: "maximize" }, { g: "close" }]
                    delegate: Item {
                        width: 46
                        height: titleBar.height
                        Rectangle {
                            anchors.fill: parent
                            color: !btnArea.containsMouse ? "transparent"
                                   : (modelData.g === "close" ? "#c42b1c" : Theme.hover)
                        }
                        SysIcon {
                            anchors.centerIn: parent
                            glyph: modelData.g
                            width: 12; height: 12
                            color: btnArea.containsMouse && modelData.g === "close"
                                   ? "#ffffff" : Theme.textPrimary
                        }
                        MouseArea { id: btnArea; anchors.fill: parent; hoverEnabled: true }
                    }
                }
            }
        }

        Item {
            id: body
            anchors.top: titleBar.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
        }
    }
}
