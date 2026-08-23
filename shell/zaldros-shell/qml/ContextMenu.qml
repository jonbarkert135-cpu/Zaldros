import QtQuick
import ZaldrosTheme

// Windows 11 style context menu: 8 px radius, acrylic surface, 32 px items, separator, and the
// "Показать дополнительные параметры" escape hatch at the bottom.
Item {
    id: menu
    property bool shown: false
    property var items: []
    property int menuWidth: 260
    signal itemChosen(string action)

    width: menuWidth
    height: column.implicitHeight + 8
    visible: opacity > 0.01
    opacity: shown ? 1 : 0
    scale: shown ? 1 : 0.97
    enabled: shown
    transformOrigin: Item.TopLeft
    Behavior on opacity { NumberAnimation { duration: Theme.animFast } }
    Behavior on scale { NumberAnimation { duration: Theme.animFast; easing.type: Easing.OutCubic } }

    Rectangle {
        anchors.fill: parent
        radius: Theme.radiusMedium
        color: Theme.dark ? "#f5292929" : "#f8fbfbfb"
        border.width: 1
        border.color: Theme.borderStrong

        Column {
            id: column
            anchors.fill: parent
            anchors.margins: 4
            spacing: 0
            Repeater {
                model: menu.items
                delegate: Item {
                    width: column.width
                    height: modelData.separator ? 7 : Theme.menuItemHeight
                    Rectangle {
                        visible: modelData.separator === true
                        anchors.centerIn: parent
                        width: parent.width - 16
                        height: 1
                        color: Theme.border
                    }
                    Rectangle {
                        visible: !modelData.separator
                        anchors.fill: parent
                        radius: Theme.radiusSmall
                        color: itemArea.containsMouse ? Theme.hover : "transparent"
                    }
                    Row {
                        visible: !modelData.separator
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.left: parent.left
                        anchors.leftMargin: 12
                        spacing: 12
                        SysIcon {
                            glyph: modelData.glyph && modelData.glyph !== "chevron-right"
                                   ? modelData.glyph : ""
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
                        visible: !modelData.separator && modelData.glyph === "chevron-right"
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
