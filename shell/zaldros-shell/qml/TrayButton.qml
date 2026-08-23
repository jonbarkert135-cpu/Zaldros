import QtQuick
import ZaldrosTheme

Item {
    id: root
    property string glyph: ""
    property string tooltip: ""
    property bool highlighted: false
    property alias content: holder.data
    signal triggered()

    width: 32
    height: Theme.taskbarHeight

    Rectangle {
        anchors.centerIn: parent
        width: root.width - 2
        height: 36
        radius: Theme.radiusSmall
        color: area.pressed ? Theme.pressed
                            : (root.highlighted ? Theme.selected
                                                : (area.containsMouse ? Theme.hover : "transparent"))
        Behavior on color { ColorAnimation { duration: Theme.animFast } }
    }

    Item { id: holder; anchors.fill: parent }

    SysIcon {
        visible: root.glyph !== ""
        anchors.centerIn: parent
        glyph: root.glyph
        width: Theme.trayIcon
        height: Theme.trayIcon
        color: Theme.textPrimary
    }

    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        onClicked: root.triggered()
    }

    ToolTipLabel {
        visible: area.containsMouse && root.tooltip !== ""
        text: root.tooltip
        anchors.right: parent.right
        anchors.bottom: parent.top
        anchors.bottomMargin: 6
        z: 50
    }
}
