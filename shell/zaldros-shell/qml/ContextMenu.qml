import QtQuick
import ZaldrosTheme

// Windows 11 context menu, measured from assets/refs/win11_context_menu.png: 8 px radius, 4 px
// padding, 32 px items with a 4 px hover plate inset by 4 px, 16 px leading glyph column,
// shortcut text and submenu chevrons on the right, a hairline separator, and a drop shadow.
Item {
    id: menu
    property bool shown: false
    property var items: []
    property int menuWidth: 300
    signal itemChosen(string action)

    width: menuWidth
    height: column.implicitHeight + Theme.menuPadding * 2
    visible: opacity > 0.01
    opacity: shown ? 1 : 0
    scale: shown ? 1 : 0.97
    enabled: shown
    transformOrigin: Item.TopLeft
    Behavior on opacity { NumberAnimation { duration: Theme.animFast } }
    Behavior on scale { NumberAnimation { duration: Theme.animFast; easing.type: Easing.OutCubic } }

    // drop shadow, drawn as offset plates (no GPU effects in the headless renderer)
    Repeater {
        model: [{ m: 8, o: 0.18 }, { m: 4, o: 0.20 }, { m: 1, o: 0.22 }]
        delegate: Rectangle {
            anchors.fill: parent
            anchors.margins: -modelData.m
            anchors.topMargin: -modelData.m + 2
            radius: Theme.radiusMedium + modelData.m
            color: "#000000"
            opacity: modelData.o
            z: -1
        }
    }

    // Opaque base under the acrylic tint: without it whatever sits behind the menu reads straight
    // through the text (a defect this shell shipped once already).
    Rectangle {
        anchors.fill: parent
        radius: Theme.radiusMedium
        color: Theme.background
    }

    Rectangle {
        anchors.fill: parent
        radius: Theme.radiusMedium
        color: Theme.dark ? "#f52c2c2c" : "#f8fbfbfb"
        border.width: 1
        border.color: Theme.borderStrong

        Column {
            id: column
            anchors.fill: parent
            anchors.margins: Theme.menuPadding
            spacing: 0
            Repeater {
                model: menu.items
                delegate: Item {
                    width: column.width
                    height: modelData.separator ? 7 : Theme.menuItemHeight
                    Rectangle {
                        visible: modelData.separator === true
                        anchors.centerIn: parent
                        width: parent.width - 8
                        height: 1
                        color: Theme.border
                    }
                    Rectangle {
                        visible: !modelData.separator
                        anchors.fill: parent
                        anchors.leftMargin: 1
                        anchors.rightMargin: 1
                        radius: Theme.radiusSmall
                        color: itemArea.pressed ? Theme.pressed
                               : (itemArea.containsMouse ? Theme.hover : "transparent")
                    }
                    Row {
                        visible: !modelData.separator
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.left: parent.left
                        anchors.leftMargin: 12
                        spacing: 14
                        SysIcon {
                            glyph: modelData.glyph ? modelData.glyph : ""
                            visible: glyph !== ""
                            width: 16; height: 16
                            color: Theme.textPrimary
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Text {
                            text: modelData.label ? modelData.label : ""
                            color: Theme.textPrimary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontCaption + 1
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }
                    SysIcon {
                        visible: !modelData.separator && modelData.submenu === true
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.right: parent.right
                        anchors.rightMargin: 12
                        glyph: "chevron-right"
                        width: 12; height: 12
                        color: Theme.textSecondary
                    }
                    Text {
                        visible: !modelData.separator && modelData.shortcut !== undefined
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.right: parent.right
                        anchors.rightMargin: 12
                        text: modelData.shortcut ? modelData.shortcut : ""
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontCaption
                    }
                    MouseArea {
                        id: itemArea
                        anchors.fill: parent
                        hoverEnabled: true
                        enabled: !modelData.separator
                        onClicked: menu.itemChosen(modelData.action ? modelData.action : "")
                    }
                }
            }
        }
    }
}
