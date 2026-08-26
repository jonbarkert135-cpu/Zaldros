import QtQuick
import ZaldrosTheme

// Labelled command-bar button ("Создать", "Сортировать", …): 16 px glyph, label, optional trailing
// chevron, 32 px tall.
Item {
    id: root
    property string glyph: ""
    property string label: ""
    property string trailing: ""
    signal triggered()

    width: row.implicitWidth + 20
    height: 32

    Rectangle {
        anchors.fill: parent
        radius: Theme.radiusSmall
        color: area.pressed ? Theme.pressed : (area.containsMouse ? Theme.hover : "transparent")
        Behavior on color { ColorAnimation { duration: Theme.animFast } }
    }
    Row {
        id: row
        anchors.centerIn: parent
        spacing: 8
        SysIcon {
            visible: root.glyph !== ""
            glyph: root.glyph
            width: 16; height: 16
            color: Theme.textPrimary
            anchors.verticalCenter: parent.verticalCenter
        }
        Text {
            text: root.label
            color: Theme.textPrimary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontCaption
            anchors.verticalCenter: parent.verticalCenter
        }
        SysIcon {
            visible: root.trailing !== ""
            glyph: root.trailing
            width: 10; height: 10
            color: Theme.textSecondary
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
