import QtQuick
import ZaldrosTheme

// A taskbar application button. Windows 11 geometry: 40x40 hit target inside a 48 px bar, 24 px
// icon, 3 px running indicator that widens when the window is active.
Item {
    id: button
    property string appName: ""
    property string initial: "?"
    property color tileColor: Theme.accent
    property bool running: false
    property bool active: false
    property bool installed: true
    property bool showTile: true
    signal activated()
    signal contextRequested(int mouseX, int mouseY)

    width: Theme.taskbarButton
    height: Theme.taskbarButton

    Rectangle {
        id: bg
        anchors.fill: parent
        radius: Theme.radiusSmall + 1
        color: area.pressed ? Theme.pressed : (area.containsMouse ? Theme.hover : "transparent")
        Behavior on color { ColorAnimation { duration: Theme.animFast } }
    }

    AppTile {
        visible: button.showTile
        anchors.centerIn: parent
        width: Theme.taskbarIcon
        height: Theme.taskbarIcon
        baseColor: button.tileColor
        label: button.initial
        dim: !button.installed
    }

    Rectangle {
        id: indicator
        visible: button.running
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 2
        height: 3
        radius: 1.5
        width: button.active ? 16 : 6
        color: button.active ? Theme.accent : Theme.textSecondary
        Behavior on width { NumberAnimation { duration: Theme.animNormal; easing.type: Easing.OutCubic } }
    }

    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        onClicked: function(mouse) {
            if (mouse.button === Qt.RightButton)
                button.contextRequested(button.x + mouse.x, mouse.y);
            else
                button.activated();
        }
    }

    ToolTipLabel {
        visible: area.containsMouse && button.appName !== ""
        text: button.appName + (button.installed ? "" : " · не установлено")
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.top
        anchors.bottomMargin: 8
    }
}
