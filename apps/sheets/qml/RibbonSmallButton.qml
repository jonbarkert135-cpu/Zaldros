import QtQuick

Item {
    property string icon: ""
    width: 22; height: 22
    Image {
        anchors.centerIn: parent
        source: "image://zaldrosicon/fluent/" + icon
        sourceSize.width: 16; sourceSize.height: 16
        width: 16; height: 16
    }
}
