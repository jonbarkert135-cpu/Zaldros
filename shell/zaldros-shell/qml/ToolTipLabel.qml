import QtQuick
import ZaldrosTheme

Rectangle {
    property alias text: label.text
    width: label.implicitWidth + 20
    height: 28
    radius: Theme.radiusSmall
    color: Theme.surfaceElevated
    border.width: 1
    border.color: Theme.border
    Text {
        id: label
        anchors.centerIn: parent
        color: Theme.textPrimary
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontCaption
    }
}
