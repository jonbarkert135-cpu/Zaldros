import QtQuick

Column {
    property string icon: ""
    property string label: ""
    spacing: 2
    width: 54

    Image {
        anchors.horizontalCenter: parent.horizontalCenter
        source: "image://zaldrosicon/fluent/" + icon
        sourceSize.width: 30; sourceSize.height: 30
        width: 30; height: 30
    }
    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        text: label; color: theme.text
        font.family: theme.family; font.pixelSize: 12
    }
    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        text: "\u2304"; color: theme.text; font.pixelSize: 10
    }
}
