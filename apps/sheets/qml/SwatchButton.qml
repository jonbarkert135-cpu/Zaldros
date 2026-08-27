import QtQuick

Item {
    property string letter: "A"
    property color swatch: "#ffd400"
    width: 24; height: 24
    Text {
        anchors { horizontalCenter: parent.horizontalCenter; top: parent.top }
        text: letter; color: theme.text
        font.family: theme.family; font.pixelSize: 13; font.bold: true
    }
    Rectangle {
        anchors { horizontalCenter: parent.horizontalCenter; bottom: parent.bottom }
        width: 16; height: 4; color: swatch
    }
}
