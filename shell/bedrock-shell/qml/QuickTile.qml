import QtQuick
import BedrockTheme

Item {
    id: tile
    property string glyph: ""
    property string label: ""
    property string detail: ""
    property bool on: false
    property bool available: true
    width: 100
    height: 68

    Rectangle {
        anchors.fill: parent
        radius: Theme.radiusSmall + 1
        color: !tile.available ? Theme.hover
               : (tile.on ? Theme.accent
               : (area.containsMouse ? Theme.selected : Theme.surface))
        border.width: 1
        border.color: Theme.border
        opacity: tile.available ? 1.0 : 0.55
        Behavior on color { ColorAnimation { duration: Theme.animFast } }
    }
    Column {
        anchors.centerIn: parent
        spacing: 5
        SysIcon {
            anchors.horizontalCenter: parent.horizontalCenter
            glyph: tile.glyph
            width: 18; height: 18
            color: tile.on && tile.available ? Theme.accentText : Theme.textPrimary
            dim: !tile.available
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            width: tile.width - 12
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
            text: tile.label
            color: tile.on && tile.available ? Theme.accentText : Theme.textPrimary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontCaption - 1
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            width: tile.width - 12
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
            visible: !tile.available
            text: tile.detail
            color: Theme.textDisabled
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontCaption - 2
        }
    }
    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        enabled: tile.available
    }
}
