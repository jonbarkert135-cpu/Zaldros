import QtQuick
import BedrockTheme

Item {
    id: root
    property string label: ""
    property string trailingGlyph: ""
    signal triggered()
    width: row.implicitWidth + 24
    height: 28

    Rectangle {
        anchors.fill: parent
        radius: Theme.radiusSmall
        color: area.pressed ? Theme.pressed : (area.containsMouse ? Theme.hover : "transparent")
        border.width: 1
        border.color: area.containsMouse ? Theme.border : "transparent"
        Behavior on color { ColorAnimation { duration: Theme.animFast } }
    }
    Row {
        id: row
        anchors.centerIn: parent
        spacing: 6
        Text {
            text: root.label
            color: Theme.textPrimary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontCaption + 1
            anchors.verticalCenter: parent.verticalCenter
        }
        SysIcon {
            visible: root.trailingGlyph !== ""
            glyph: root.trailingGlyph
            width: 12; height: 12
            color: Theme.textPrimary
            anchors.verticalCenter: parent.verticalCenter
        }
    }
    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        onClicked: root.triggered()
    }
}
