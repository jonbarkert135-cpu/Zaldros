// One ribbon group: its controls, a separator, and the caption Excel puts under them.
import QtQuick

Item {
    id: group
    property string caption: ""
    default property alias content: holder.data
    height: parent ? parent.height : 105

    Item {
        id: holder
        anchors { left: parent.left; right: parent.right; top: parent.top
                  leftMargin: 10; rightMargin: 10; topMargin: 8 }
        height: parent.height - 26
    }
    Text {
        anchors { horizontalCenter: parent.horizontalCenter; bottom: parent.bottom
                  bottomMargin: 4 }
        text: group.caption
        color: theme.text
        font.family: theme.family
        font.pixelSize: 11
        opacity: 0.85
    }
    Rectangle {
        anchors { right: parent.right; top: parent.top; bottom: parent.bottom
                  topMargin: 8; bottomMargin: 8 }
        width: 1
        color: theme.gridline
    }
}
