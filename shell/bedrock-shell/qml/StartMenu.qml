import QtQuick
import BedrockTheme
import QtQuick.Layouts

// Bedrock Start — the Windows 11 structure: search field, "Закреплено" grid, "Рекомендуем" list,
// and a footer with the user and the power button.
Rectangle {
    id: start
    property bool shown: false
    required property var state   // injected by Shell.qml (see Taskbar.qml)
    required property var apps
    signal appLaunched(string execName)

    width: Theme.startWidth
    height: Theme.startHeight
    radius: Theme.startRadius
    color: Theme.surface
    border.color: Theme.stroke
    border.width: 1

    opacity: shown ? 1 : 0
    visible: opacity > 0
    transform: Translate { y: start.shown ? 0 : 24 }
    Behavior on opacity { NumberAnimation { duration: Theme.animNormal; easing.type: Easing.OutCubic } }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 16

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 36
            radius: 18
            color: Theme.surfaceAlt
            border.color: Theme.stroke
            Row {
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left; anchors.leftMargin: 14
                spacing: 8
                Text { text: "🔍"; color: Theme.textDim; font.pixelSize: 13 }
                Text { text: "Введите здесь текст для поиска"; color: Theme.textDim
                       font.pixelSize: 13; font.family: Theme.fontFamily }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Text { text: "Закреплено"; color: Theme.text; font.pixelSize: 14; font.bold: true
                   font.family: Theme.fontFamily }
            Item { Layout.fillWidth: true }
            Text { text: "Все приложения  ›"; color: Theme.textDim; font.pixelSize: 12
                   font.family: Theme.fontFamily }
        }

        GridView {
            Layout.fillWidth: true
            Layout.preferredHeight: 300
            cellWidth: width / 6
            cellHeight: 96
            interactive: false
            model: start.apps
            delegate: Item {
                width: GridView.view.cellWidth
                height: GridView.view.cellHeight
                Rectangle {
                    anchors.fill: parent
                    anchors.margins: 4
                    radius: 6
                    color: tile.containsMouse ? Theme.hover : "transparent"
                    Behavior on color { ColorAnimation { duration: Theme.animFast } }
                }
                Column {
                    anchors.centerIn: parent
                    spacing: 8
                    Rectangle {
                        width: 32; height: 32; radius: 6
                        color: model.color
                        anchors.horizontalCenter: parent.horizontalCenter
                        Text { anchors.centerIn: parent; text: model.icon; font.pixelSize: 16
                               color: "white" }
                    }
                    Text {
                        text: model.name
                        color: Theme.text; font.pixelSize: 11; font.family: Theme.fontFamily
                        width: 84; horizontalAlignment: Text.AlignHCenter
                        elide: Text.ElideRight
                        anchors.horizontalCenter: parent.horizontalCenter
                    }
                }
                MouseArea {
                    id: tile
                    anchors.fill: parent; hoverEnabled: true
                    onClicked: start.appLaunched(model.execName)
                }
            }
        }

        Text { text: "Рекомендуем"; color: Theme.text; font.pixelSize: 14; font.bold: true
               font.family: Theme.fontFamily }

        // Deliberately empty: recommendations require a real usage history service, which does not
        // exist yet. Showing invented "recent files" would be a fake system state (PART 3 §25).
        Text {
            Layout.fillWidth: true
            text: "Здесь появятся недавние файлы и приложения.\nСлужба истории использования ещё не реализована."
            color: Theme.textDim; font.pixelSize: 12; font.family: Theme.fontFamily
            lineHeight: 1.3
        }

        Item { Layout.fillHeight: true }

        RowLayout {
            Layout.fillWidth: true
            Rectangle { width: 28; height: 28; radius: 14; color: "#4b6a8a"
                        Text { anchors.centerIn: parent; text: "L"; color: "white"; font.pixelSize: 13 } }
            Text { text: "Пользователь"; color: Theme.text; font.pixelSize: 12
                   font.family: Theme.fontFamily; Layout.leftMargin: 8 }
            Item { Layout.fillWidth: true }
            Text {
                text: start.state.memoryPercent >= 0 ? "ОЗУ " + start.state.memoryPercent + "%" : "ОЗУ —"
                color: Theme.textDim; font.pixelSize: 11; font.family: Theme.fontFamily
            }
            Text { text: "⏻"; color: Theme.text; font.pixelSize: 15; Layout.leftMargin: 12 }
        }
    }
}
