// B / I / U and the number-format letters. Letterforms, drawn by our own UI font.
import QtQuick

Item {
    property string letter: ""
    property bool bold: false
    property bool italic: false
    property bool underline: false
    width: 24; height: 22
    Text {
        anchors.centerIn: parent
        text: letter
        color: theme.text
        font.family: theme.family
        font.pixelSize: 14
        font.bold: bold
        font.italic: italic
        font.underline: underline
    }
}
