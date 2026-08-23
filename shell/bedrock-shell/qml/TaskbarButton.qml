import QtQuick
import BedrockTheme

// A taskbar item: icon, hover highlight, and the Windows-style "running" underline.
Item {
    id: root
    property string glyph: ""
    property color  glyphColor: Theme.accent
    property string tooltip: ""
    property bool   running: false
    property bool   active: false
    signal activated()

    width: Theme.buttonSize
    height: Theme.buttonSize

    Rectangle {
        anchors.fill: parent
        radius: 6
        color: mouse.pressed ? Theme.pressed : (mouse.containsMouse ? Theme.hover : "transparent")
        Behavior on color { ColorAnimation { duration: Theme.animFast } }
    }

    Rectangle {
        anchors.centerIn: parent
        width: Theme.iconSize; height: Theme.iconSize
        radius: 5
        color: root.glyphColor
        Text {
            anchors.centerIn: parent
            text: root.glyph
            color: "white"
            font.pixelSize: 13
            font.family: Theme.fontFamily
        }
    }

    // Windows 11 shows a short underline for a running app, wider when it is focused.
    Rectangle {
        visible: root.running
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 2
        height: 3; radius: 2
        width: root.active ? 16 : 6
        color: Theme.accent
        Behavior on width { NumberAnimation { duration: Theme.animNormal; easing.type: Easing.OutCubic } }
    }

    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        onClicked: root.activated()
    }
}
