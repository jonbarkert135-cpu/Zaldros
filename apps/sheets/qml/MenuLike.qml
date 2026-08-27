import QtQuick

Row {
    property string text: ""
    spacing: 6
    Text {
        text: parent.text; color: theme.text
        font.family: theme.family; font.pixelSize: 13
    }
    Text { text: "\u2304"; color: theme.text; font.pixelSize: 11 }
}
