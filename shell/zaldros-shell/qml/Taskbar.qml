import QtQuick
import ZaldrosTheme

// Zaldros Taskbar. Windows 11 layout: 48 px bar, centred Start + search + app group, tray on the
// right with two-line clock. Everything shown here is either real (clock, running processes,
// network/battery presence) or explicitly marked unavailable.
Item {
    id: taskbar
    property var state: null
    property var system: null
    property var apps: null
    property bool startActive: false
    property bool quickActive: false
    property string activeApp: ""
    signal startToggled()
    signal quickToggled()
    signal appActivated(int row)
    signal searchRequested()
    signal contextRequested(int posX)

    height: Theme.taskbarHeight

    Rectangle {
        anchors.fill: parent
        color: Theme.taskbarBg
        Rectangle {
            anchors.top: parent.top
            width: parent.width
            height: 1
            color: Theme.border
        }
        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.RightButton
            onClicked: function(mouse) { taskbar.contextRequested(mouse.x) }
        }
    }

    // --- centre group: Start, search, pinned + running applications ------------------------
    Row {
        id: centreGroup
        anchors.centerIn: parent
        spacing: 4

        TaskbarButton {
            id: startButton
            appName: "Пуск"
            showTile: false
            running: false
            width: Theme.taskbarButton
            height: Theme.taskbarButton
            onActivated: taskbar.startToggled()
            ZaldrosMark {
                anchors.centerIn: parent
                width: Theme.taskbarIcon
                height: Theme.taskbarIcon
                color: taskbar.startActive ? Theme.accent : Theme.textPrimary
                z: 2
            }
        }

        Item {
            width: searchPill.width
            height: Theme.taskbarButton
            Rectangle {
                id: searchPill
                anchors.verticalCenter: parent.verticalCenter
                width: 180
                height: 32
                radius: 16
                color: searchArea.containsMouse ? Theme.selected : Theme.hover
                border.width: 1
                border.color: Theme.border
                Behavior on color { ColorAnimation { duration: Theme.animFast } }
                Row {
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.left: parent.left
                    anchors.leftMargin: 10
                    spacing: 8
                    SysIcon {
                        glyph: "search"
                        width: 16; height: 16
                        color: Theme.textSecondary
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    Text {
                        text: "Поиск"
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontCaption + 1
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }
                MouseArea {
                    id: searchArea
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: taskbar.searchRequested()
                }
            }
        }

        Repeater {
            model: taskbar.apps
            delegate: TaskbarButton {
                appName: model.name
                initial: model.name.substring(0, 1).toUpperCase()
                tileColor: model.color
                running: model.running
                installed: model.installed
                active: model.running && model.name === taskbar.activeApp
                onActivated: taskbar.appActivated(index)
            }
        }
    }

    // --- system tray ------------------------------------------------------------------------
    Row {
        id: tray
        anchors.right: parent.right
        anchors.rightMargin: 4
        anchors.verticalCenter: parent.verticalCenter
        spacing: 0

        // hidden-items overflow chevron, exactly as Windows 11 places it
        TrayButton {
            glyph: "chevron-up"
            tooltip: "Скрытые значки"
        }

        TrayButton {
            id: quickButton
            width: 78
            highlighted: taskbar.quickActive
            tooltip: taskbar.system
                     ? ("Сеть: " + taskbar.system.networkDetail
                        + " · Звук: " + taskbar.system.volumeDetail
                        + " · Батарея: " + taskbar.system.batteryDetail)
                     : "нет данных"
            onTriggered: taskbar.quickToggled()
            content: Row {
                spacing: 8
                anchors.centerIn: parent
                SysIcon {
                    glyph: taskbar.system && taskbar.system.networkDetail.indexOf("Wi-Fi") >= 0
                           ? "wifi" : "ethernet"
                    width: Theme.trayIcon; height: Theme.trayIcon
                    color: Theme.textPrimary
                    dim: !(taskbar.system && taskbar.system.networkAvailable)
                }
                SysIcon {
                    glyph: "volume"
                    width: Theme.trayIcon; height: Theme.trayIcon
                    color: Theme.textPrimary
                    dim: !(taskbar.system && taskbar.system.volumeAvailable)
                }
                SysIcon {
                    glyph: "battery"
                    width: Theme.trayIcon; height: Theme.trayIcon
                    color: Theme.textPrimary
                    dim: !(taskbar.system && taskbar.system.batteryAvailable)
                }
            }
        }

        // two-line clock: time above date, right aligned (Windows 11)
        TrayButton {
            width: clockColumn.implicitWidth + 20
            tooltip: "Календарь"
            content: Column {
                id: clockColumn
                anchors.centerIn: parent
                spacing: 0
                Text {
                    text: taskbar.state ? taskbar.state.timeText : ""
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontCaption
                    horizontalAlignment: Text.AlignRight
                    anchors.right: parent.right
                }
                Text {
                    text: taskbar.state ? taskbar.state.dateText : ""
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontCaption
                    horizontalAlignment: Text.AlignRight
                    anchors.right: parent.right
                }
            }
        }

        TrayButton {
            glyph: "bell"
            tooltip: "Уведомления"
        }

        // "Show desktop" strip at the very edge — Windows keeps a thin hot zone here
        Item {
            width: 6
            height: Theme.taskbarHeight
            Rectangle {
                anchors.centerIn: parent
                width: 1
                height: 24
                color: Theme.border
            }
        }
    }
}
