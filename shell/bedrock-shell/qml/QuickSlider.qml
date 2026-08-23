import QtQuick
import BedrockTheme

Item {
    id: root
    property string glyph: ""
    property string label: ""
    property int value: -1
    property bool available: false
    property string unavailableText: "нет данных"
    height: 34

    Row {
        anchors.fill: parent
        spacing: 12
        SysIcon {
            glyph: root.glyph
            width: 16; height: 16
            color: Theme.textPrimary
            dim: !root.available
            anchors.verticalCenter: parent.verticalCenter
        }
        Item {
            width: parent.width - 28
            height: parent.height
            Rectangle {
                id: track
                anchors.verticalCenter: parent.verticalCenter
                width: parent.width
                height: 4
                radius: 2
                color: Theme.borderStrong
                opacity: root.available ? 1 : 0.5
            }
            Rectangle {
                visible: root.available && root.value >= 0
                anchors.verticalCenter: parent.verticalCenter
                width: track.width * Math.max(0, root.value) / 100
                height: 4
                radius: 2
                color: Theme.accent
            }
            Rectangle {
                visible: root.available && root.value >= 0
                width: 16; height: 16; radius: 8
                color: Theme.accent
                border.width: 3
                border.color: Theme.background
                anchors.verticalCenter: parent.verticalCenter
                x: track.width * Math.max(0, root.value) / 100 - 8
            }
            Text {
                visible: !root.available
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                text: root.label + " — " + root.unavailableText
                color: Theme.textDisabled
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontCaption
            }
        }
    }
}
