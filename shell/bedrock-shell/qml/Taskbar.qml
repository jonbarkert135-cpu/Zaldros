import QtQuick
import BedrockTheme
import QtQuick.Layouts

// Bedrock Taskbar — centred icon group, left-aligned nothing, right-aligned system tray + clock,
// which is the Windows 11 layout. Real behaviour implemented here: hover states, running underline,
// Start toggle, live clock from the backend.
Item {
    id: taskbar
    property alias startActive: startButton.active
    // Injected by Shell.qml. Context properties are not visible to types loaded through a qmldir
    // module, so the backend objects are passed down explicitly instead.
    required property var state
    required property var apps
    signal startToggled()
    signal appActivated(string execName)

    height: Theme.taskbarHeight

    Rectangle {
        anchors.fill: parent
        color: Theme.taskbarBg
        Rectangle { // 1px top hairline, as on the reference
            width: parent.width; height: 1
            color: Theme.stroke
        }
    }

    // ---- centre group: Start, search, pinned/running apps ----
    RowLayout {
        anchors.centerIn: parent
        spacing: 4

        TaskbarButton {
            id: startButton
            glyph: "⊞"
            glyphColor: "#0a84ff"
            tooltip: "Пуск"
            onActivated: taskbar.startToggled()
        }

        // Search pill — Windows 11 keeps a wide search box next to Start.
        Rectangle {
            Layout.preferredWidth: 180
            Layout.preferredHeight: 32
            radius: 16
            color: searchArea.containsMouse ? Theme.pressed : Theme.surfaceAlt
            border.color: Theme.stroke
            border.width: 1
            Behavior on color { ColorAnimation { duration: Theme.animFast } }
            Row {
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                anchors.leftMargin: 10
                spacing: 8
                Text { text: "🔍"; font.pixelSize: 12; color: Theme.textDim
                       anchors.verticalCenter: parent.verticalCenter }
                Text { text: "Поиск"; font.pixelSize: 12; color: Theme.textDim
                       font.family: Theme.fontFamily
                       anchors.verticalCenter: parent.verticalCenter }
            }
            MouseArea { id: searchArea; anchors.fill: parent; hoverEnabled: true }
        }

        Repeater {
            model: taskbar.apps
            delegate: TaskbarButton {
                glyph: model.icon
                glyphColor: model.color
                tooltip: model.name
                running: model.running
                active: model.running && index === 0
                onActivated: taskbar.appActivated(model.execName)
            }
        }
    }

    // ---- right group: tray + clock ----
    RowLayout {
        anchors.right: parent.right
        anchors.rightMargin: 12
        anchors.verticalCenter: parent.verticalCenter
        spacing: 12

        Row {
            spacing: 10
            // Tray glyphs are placeholders until the real NetworkManager/PipeWire/UPower backends
            // exist. They intentionally show a neutral state instead of a fake signal strength.
            Text { text: "^"; color: Theme.textDim; font.pixelSize: 12 }
            Text { text: "🔊"; color: Theme.textDim; font.pixelSize: 12 }
            Text { text: "🖧"; color: Theme.textDim; font.pixelSize: 12 }
        }

        Column {
            spacing: 0
            Text {
                text: taskbar.state.timeText
                color: Theme.text; font.pixelSize: 12; font.family: Theme.fontFamily
                horizontalAlignment: Text.AlignRight
                anchors.right: parent.right
            }
            Text {
                text: taskbar.state.dateText
                color: Theme.text; font.pixelSize: 11; font.family: Theme.fontFamily
                horizontalAlignment: Text.AlignRight
                anchors.right: parent.right
            }
        }
    }
}
