import QtQuick
import ZaldrosTheme

// One Settings row card. Measured from the Windows 11 capture: 74 px tall, 4 px radius, 6 px gap,
// icon on the left, title over a secondary line, value and chevron on the right.
Item {
    id: card
    property string glyph: ""
    property string title: ""
    property string detail: ""
    property string value: ""
    property bool hasToggle: false      // a real switch, not decoration
    property bool toggled: false
    property bool navigable: true       // chevron only when the row opens another page
    signal triggered()
    signal toggledChanged2()

    height: 74

    Rectangle {
        anchors.fill: parent
        radius: Theme.radiusSmall
        color: area.pressed ? Theme.pressed
               : (area.containsMouse ? Qt.lighter(Theme.surfaceCard, 1.15) : Theme.surfaceCard)
        border.width: 1
        border.color: Theme.border
        Behavior on color { ColorAnimation { duration: Theme.animFast } }
    }

    Row {
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: parent.left
        anchors.leftMargin: 20
        spacing: 18
        SysIcon {
            visible: card.glyph !== ""
            glyph: card.glyph
            width: 20; height: 20
            color: Theme.textPrimary
            anchors.verticalCenter: parent.verticalCenter
        }
        Column {
            anchors.verticalCenter: parent.verticalCenter
            spacing: 3
            Text {
                text: card.title
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBody
            }
            Text {
                visible: card.detail !== ""
                text: card.detail
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontCaption
            }
        }
    }

    Row {
        anchors.verticalCenter: parent.verticalCenter
        anchors.right: parent.right
        anchors.rightMargin: 18
        spacing: 14
        Text {
            visible: card.value !== ""
            anchors.verticalCenter: parent.verticalCenter
            text: card.value
            color: Theme.textSecondary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontCaption
        }
        // Windows 11 switch: 40x20 track, 12 px knob that slides to the right when on.
        Rectangle {
            visible: card.hasToggle
            anchors.verticalCenter: parent.verticalCenter
            width: 40; height: 20; radius: 10
            color: card.toggled ? Theme.accent : "transparent"
            border.width: card.toggled ? 0 : 1
            border.color: Theme.textSecondary
            Rectangle {
                width: 12; height: 12; radius: 6
                y: 4
                x: card.toggled ? parent.width - width - 4 : 4
                color: card.toggled ? "#ffffff" : Theme.textSecondary
                Behavior on x { NumberAnimation { duration: Theme.animFast } }
            }
        }
        SysIcon {
            visible: card.navigable
            anchors.verticalCenter: parent.verticalCenter
            glyph: "chevron-right"
            width: 12; height: 12
            color: Theme.textSecondary
        }
    }

    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        onClicked: card.triggered()
    }
}
