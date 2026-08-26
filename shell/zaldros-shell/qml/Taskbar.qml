import QtQuick
import ZaldrosTheme

// Zaldros taskbar, built to the measured Windows 11 layout (system/theme/win11-reference.json):
// 48 px bar, centred group of 44 px buttons holding Start, the search field, task view and the
// application buttons, and a right-hand tray of 36 px buttons ending in the two-line clock.
// Everything shown is real (clock, running processes, network/battery presence) or marked absent.
Item {
    id: taskbar
    objectName: "taskbar"

    property var state: null
    property var system: null
    property var apps: null
    property var weather: null
    property bool startActive: false
    property bool quickActive: false
    property bool searchActive: false
    property bool notificationsActive: false
    property bool taskViewActive: false
    property string activeApp: ""
    // Buttons for the windows the shell itself owns: [{ id, name, glyph, running, active }]
    property var windowButtons: []

    signal startToggled()
    signal quickToggled()
    signal searchToggled()
    signal notificationsToggled()
    signal taskViewToggled()
    signal appActivated(int row)
    signal windowActivated(string id)
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

    // --- widgets button: weather at the left end, where Windows 11 puts it --------------------
    // The reading is real (zaldros_shell/weather.py) or the button says it has none. Measured
    // from the reference: icon left edge 20 px, 24 px icon, two text lines beside it.
    Item {
        id: widgets
        objectName: "widgetsButton"
        anchors.verticalCenter: parent.verticalCenter
        height: Theme.taskbarButtonHeight
        // The hover pill starts 12 px in; the icon then sits at the measured 20 px from the edge.
        x: 12
        width: (Theme.taskbarWidgetLeft - 12) + Theme.taskbarIcon + Theme.taskbarWidgetGap
               + weatherText.implicitWidth + 14

        Rectangle {
            anchors.fill: parent
            radius: Theme.radiusSmall
            color: widgetsArea.containsMouse ? Theme.hover : "transparent"
            Behavior on color { ColorAnimation { duration: Theme.animFast } }
        }

        SysIcon {
            id: weatherIcon
            objectName: "weatherIcon"
            x: Theme.taskbarWidgetLeft - widgets.x
            anchors.verticalCenter: parent.verticalCenter
            width: Theme.taskbarIcon
            height: Theme.taskbarIcon
            glyph: taskbar.weather && taskbar.weather.available ? taskbar.weather.glyph : "weather-cloud"
            color: Theme.textPrimary
            dim: !(taskbar.weather && taskbar.weather.available)
        }

        Column {
            id: weatherText
            anchors.left: weatherIcon.right
            anchors.leftMargin: Theme.taskbarWidgetGap - 4
            anchors.verticalCenter: parent.verticalCenter
            spacing: 0
            Text {
                objectName: "weatherTemperature"
                text: taskbar.weather && taskbar.weather.available ? taskbar.weather.temperature : "—"
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontCaption
            }
            Text {
                objectName: "weatherCondition"
                // Run #29 in the booted ISO: with no location configured the taskbar carried the
                // sentence "местоположение не задано" where Windows carries a weather condition.
                // The state is real and stays visible — dimmed icon, em dash, full explanation in
                // the tooltip — but the panel is not the place for an error message.
                text: taskbar.weather && taskbar.weather.available ? taskbar.weather.condition
                                                                   : "нет данных"
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontCaption - 1
                elide: Text.ElideRight
                width: Math.min(implicitWidth, 150)
            }
        }

        MouseArea {
            id: widgetsArea
            anchors.fill: parent
            hoverEnabled: true
            onClicked: taskbar.searchToggled()
        }
        ToolTipLabel {
            visible: widgetsArea.containsMouse
            text: taskbar.weather ? taskbar.weather.detail : "нет данных"
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.top
        }
    }

    // --- centre group: Start, search, task view, pinned + running applications ----------------
    Row {
        id: centreGroup
        objectName: "taskbarGroup"
        anchors.centerIn: parent
        spacing: 0

        TaskbarButton {
            id: startButton
            objectName: "startButton"
            appName: "Пуск"
            showTile: false
            running: false
            active: taskbar.startActive
            onActivated: taskbar.startToggled()
            ZaldrosMark {
                anchors.centerIn: parent
                width: Theme.taskbarIcon
                height: Theme.taskbarIcon
                color: taskbar.startActive ? Theme.accent : Theme.textPrimary
                z: 2
            }
        }

        // Windows 11 keeps the search field inside the centred group, immediately after Start.
        Item {
            objectName: "taskbarSearch"
            width: Theme.taskbarSearchWidth + 8
            height: Theme.taskbarHeight

            Rectangle {
                id: searchPill
                anchors.centerIn: parent
                width: Theme.taskbarSearchWidth
                height: Theme.taskbarSearchHeight
                radius: height / 2
                color: taskbar.searchActive ? Theme.selected
                       : (searchArea.containsMouse ? Theme.hover : (Theme.dark ? "#14ffffff" : "#0a000000"))
                border.width: 1
                border.color: Theme.border
                Behavior on color { ColorAnimation { duration: Theme.animFast } }

                Row {
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.left: parent.left
                    anchors.leftMargin: 12
                    spacing: 10
                    SysIcon {
                        glyph: "search"
                        width: 16; height: 16
                        color: Theme.textPrimary
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    Text {
                        text: "Поиск"
                        color: Theme.textPrimary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontCaption + 1
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }
                MouseArea {
                    id: searchArea
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: taskbar.searchToggled()
                }
            }
        }

        TaskbarButton {
            objectName: "taskViewButton"
            appName: "Представление задач"
            showTile: false
            active: taskbar.taskViewActive
            onActivated: taskbar.taskViewToggled()
            SysIcon {
                anchors.centerIn: parent
                glyph: "taskview"
                width: Theme.taskbarIcon
                height: Theme.taskbarIcon
                color: Theme.textPrimary
                z: 2
            }
        }

        Repeater {
            model: taskbar.windowButtons
            delegate: TaskbarButton {
                appName: modelData.name
                iconGlyph: modelData.glyph
                initial: modelData.name.substring(0, 1)
                running: modelData.running
                active: modelData.active
                onActivated: taskbar.windowActivated(modelData.id)
            }
        }

        // Windows 11 keeps a handful of pins on the bar; the rest of the set lives in Start.
        Repeater {
            model: taskbar.apps ? taskbar.apps.taskbarPins : []
            delegate: TaskbarButton {
                appName: modelData.name
                initial: modelData.name.substring(0, 1).toUpperCase()
                tileColor: modelData.color
                iconName: modelData.icon
                running: modelData.running
                installed: modelData.installed
                active: modelData.running && modelData.name === taskbar.activeApp
                onActivated: taskbar.appActivated(modelData.row)
            }
        }
    }

    // --- system tray ---------------------------------------------------------------------------
    Row {
        id: tray
        objectName: "trayGroup"
        anchors.right: parent.right
        anchors.rightMargin: Theme.taskbarRightMargin
        anchors.verticalCenter: parent.verticalCenter
        spacing: 0

        // hidden-items overflow chevron, where Windows 11 places it
        TrayButton {
            glyph: "chevron-up"
            tooltip: "Скрытые значки"
        }

        // Keyboard layout, read from the session rather than invented. Clicking it switches to
        // the next layout, which is what the badge does in Windows.
        TrayButton {
            objectName: "trayLayoutButton"
            width: layoutText.implicitWidth + 16
            tooltip: taskbar.system ? taskbar.system.keyboardDetail : "нет данных"
            onTriggered: if (taskbar.system) taskbar.system.switchLayout()
            content: Text {
                id: layoutText
                anchors.centerIn: parent
                text: taskbar.system ? taskbar.system.keyboardLayout : ""
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontCaption
            }
        }

        // network + volume + battery share one hover pill, exactly like Windows 11
        TrayButton {
            id: quickButton
            objectName: "trayQuickButton"
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

        // two-line clock: time above date, right aligned, opens the notification centre
        TrayButton {
            objectName: "clock"
            width: clockColumn.implicitWidth + 20
            highlighted: taskbar.notificationsActive
            tooltip: "Уведомления и календарь"
            onTriggered: taskbar.notificationsToggled()
            content: Column {
                id: clockColumn
                anchors.centerIn: parent
                spacing: 1
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
            objectName: "notificationButton"
            width: 28
            glyph: "bell"
            highlighted: taskbar.notificationsActive
            tooltip: "Центр уведомлений"
            onTriggered: taskbar.notificationsToggled()
        }
    }

    // "Show desktop" hot zone at the very edge — a 4 px strip, as in Windows 11
    Item {
        width: 4
        height: Theme.taskbarHeight
        anchors.right: parent.right
        Rectangle {
            anchors.centerIn: parent
            width: 1
            height: 24
            color: showDesktop.containsMouse ? Theme.textSecondary : Theme.border
        }
        MouseArea { id: showDesktop; anchors.fill: parent; hoverEnabled: true }
    }
}
