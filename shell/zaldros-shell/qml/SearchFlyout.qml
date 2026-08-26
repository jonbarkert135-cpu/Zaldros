import QtQuick
import QtQuick.Controls
import ZaldrosTheme

// Taskbar search panel. Windows 11 opens a 640 px wide panel above the search field with the query
// box at the top, a "best match" hero row and the result list beneath it.
//
// Results are this machine's installed applications (InstalledAppModel, read from .desktop files),
// filtered live. No web suggestions are faked.
Item {
    id: search
    objectName: "searchFlyout"

    property bool shown: false
    property var installed: null
    property real baseY: 0
    property string query: ""
    signal appLaunched(int row)

    width: Theme.startWidth
    height: Theme.startHeight - 160
    visible: opacity > 0.01
    opacity: shown ? 1 : 0
    y: shown ? baseY : baseY + 24
    enabled: shown
    Behavior on opacity { NumberAnimation { duration: Theme.animNormal; easing.type: Easing.OutCubic } }
    Behavior on y { NumberAnimation { duration: Theme.animSlow; easing.type: Easing.OutCubic } }

    onShownChanged: { if (shown) queryInput.forceActiveFocus(); else query = "" }

    Rectangle { anchors.fill: parent; radius: Theme.radiusMedium; color: Theme.background }

    Rectangle {
        anchors.fill: parent
        radius: Theme.radiusMedium
        color: Theme.surfaceAcrylic
        border.width: 1
        border.color: Theme.borderStrong
        clip: true

        Rectangle {
            id: queryField
            x: Theme.startPadding
            y: 24
            width: parent.width - Theme.startPadding * 2
            height: Theme.startSearchHeight
            radius: 6
            color: Theme.surface
            border.width: 1
            border.color: queryInput.activeFocus ? Theme.accent : Theme.border
            Row {
                anchors.fill: parent
                anchors.leftMargin: 12
                spacing: 10
                SysIcon {
                    glyph: "search"; width: 16; height: 16
                    color: Theme.textSecondary
                    anchors.verticalCenter: parent.verticalCenter
                }
                TextInput {
                    id: queryInput
                    width: parent.width - 50
                    anchors.verticalCenter: parent.verticalCenter
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBody
                    clip: true
                    onTextChanged: search.query = text
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        visible: queryInput.text.length === 0
                        text: "Введите запрос для поиска"
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBody
                    }
                }
            }
        }

        Text {
            id: sectionLabel
            x: Theme.startPadding
            anchors.top: queryField.bottom
            anchors.topMargin: 20
            text: search.query === "" ? "Приложения на этом компьютере" : "Результаты"
            color: Theme.textPrimary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontBody
            font.weight: Font.DemiBold
        }

        ListView {
            id: results
            x: Theme.startPadding
            anchors.top: sectionLabel.bottom
            anchors.topMargin: 10
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 20
            width: parent.width - Theme.startPadding * 2
            clip: true
            model: search.installed
            ScrollBar.vertical: ScrollBar { }
            delegate: Item {
                // filtering happens here so the list stays bound to the real model
                readonly property bool matches: search.query === ""
                    || model.name.toLowerCase().indexOf(search.query.toLowerCase()) >= 0
                visible: matches
                width: results.width
                height: matches ? 48 : 0

                Rectangle {
                    anchors.fill: parent
                    anchors.rightMargin: 8
                    anchors.bottomMargin: 2
                    radius: Theme.radiusSmall
                    color: rowArea.pressed ? Theme.pressed
                           : (rowArea.containsMouse ? Theme.hover : "transparent")
                }
                Row {
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.left: parent.left
                    anchors.leftMargin: 12
                    spacing: 14
                    AppTile {
                        width: 28; height: 28
                        baseColor: model.color
                        iconName: model.icon
                        label: model.name.substring(0, 1).toUpperCase()
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    Column {
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 2
                        Text {
                            text: model.name
                            color: Theme.textPrimary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontBody
                        }
                        Text {
                            visible: model.subtitle !== ""
                            text: model.subtitle
                            color: Theme.textSecondary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontCaption
                        }
                    }
                }
                MouseArea {
                    id: rowArea
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: search.appLaunched(index)
                }
            }
        }
    }
}
