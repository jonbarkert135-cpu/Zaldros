import QtQuick
import ZaldrosTheme

// A 32x32 command-bar / toolbar button: 16 px glyph, 4 px radius hover plate — the Windows 11
// command-bar rhythm used by Explorer and Settings.
Item {
    id: root
    property string glyph: ""
    property string tooltip: ""
    property bool enabled: true
    signal triggered()

    width: 32
    height: 32
    opacity: enabled ? 1.0 : 0.4

    Rectangle {
        anchors.fill: parent
        radius: Theme.radiusSmall
        color: !root.enabled ? "transparent"
               : (area.pressed ? Theme.pressed : (area.containsMouse ? Theme.hover : "transparent"))
        Behavior on color { ColorAnimation { duration: Theme.animFast } }
    }
    SysIcon {
        anchors.centerIn: parent
        glyph: root.glyph
        width: 16; height: 16
        color: Theme.textPrimary
    }
    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        enabled: root.enabled
        onClicked: root.triggered()
    }
    ToolTipLabel {
        visible: area.containsMouse && root.tooltip !== ""
        text: root.tooltip
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.bottom
        anchors.topMargin: 6
        z: 60
    }
}
