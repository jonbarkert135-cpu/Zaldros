import QtQuick
import ZaldrosTheme

// One taskbar button. Measured Windows 11 geometry: 44 px pitch inside the 48 px bar, a 40 px
// square hover plate, a 24 px icon and the running indicator — 6 px wide idle, 16 px when the
// window is in the foreground.
Item {
    id: button
    property string appName: ""
    property string initial: "?"
    property color tileColor: Theme.accent
    property bool running: false
    property bool active: false
    property bool installed: true
    property string iconName: ""
    property string iconGlyph: ""
    property bool showTile: true
    signal activated()
    signal contextRequested(int mouseX, int mouseY)

    width: Theme.taskbarButton
    height: Theme.taskbarHeight

    Rectangle {
        id: plate
        anchors.centerIn: parent
        width: Theme.taskbarButtonHeight
        height: Theme.taskbarButtonHeight
        radius: Theme.radiusSmall + 1
        color: area.pressed ? Theme.pressed
               : (button.active ? Theme.selected
               : (area.containsMouse ? Theme.hover : "transparent"))
        Behavior on color { ColorAnimation { duration: Theme.animFast } }
    }

    AppTile {
        visible: button.showTile
        anchors.centerIn: parent
        width: Theme.taskbarIcon
        height: Theme.taskbarIcon
        baseColor: button.tileColor
        iconName: button.iconName
        glyph: button.iconGlyph
        label: button.initial
        dim: !button.installed
    }

    Rectangle {
        id: indicator
        visible: button.running
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 3
        height: Theme.indicatorHeight
        radius: height / 2
        width: button.active ? Theme.indicatorActive : Theme.indicatorWidth
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
        z: 60
    }
}
