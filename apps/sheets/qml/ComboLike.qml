import QtQuick

Rectangle {
    property string text: ""
    height: 24
    radius: 2
    color: "transparent"
    border.color: theme.gridline
    border.width: 1
    Text {
        anchors { left: parent.left; leftMargin: 8; verticalCenter: parent.verticalCenter }
        text: parent.text; color: theme.text
        font.family: theme.family; font.pixelSize: 13
    }
    Text {
        anchors { right: parent.right; rightMargin: 6; verticalCenter: parent.verticalCenter }
        text: "\u2304"; color: theme.text; font.pixelSize: 12
    }
}
