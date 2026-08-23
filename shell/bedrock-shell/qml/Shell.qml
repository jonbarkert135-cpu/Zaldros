import QtQuick
import BedrockTheme

// Composition root of the Bedrock Shell: desktop, window layer, Start, quick settings, context
// menus and the taskbar. Backends are injected as properties by bedrock_shell/app.py.
Item {
    id: shell
    width: 1600
    height: 1000

    property bool startOpen: false
    property bool quickOpen: false
    property bool contextOpen: false
    property bool lightMode: false
    property var backendState: shellState
    property var backendApps: appModel
    property var backendInstalled: installedModel
    property var backendSystem: systemState

    onLightModeChanged: Theme.dark = !lightMode

    // --- desktop ---------------------------------------------------------------------------
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: Theme.dark ? "#123b63" : "#7fb2e5" }
            GradientStop { position: 0.55; color: Theme.dark ? "#0d2745" : "#4b81bd" }
            GradientStop { position: 1.0; color: Theme.dark ? "#08192c" : "#2d5b8f" }
        }
        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.LeftButton | Qt.RightButton
            onClicked: function(mouse) {
                shell.startOpen = false;
                shell.quickOpen = false;
                if (mouse.button === Qt.RightButton) {
                    desktopMenu.x = mouse.x;
                    desktopMenu.y = mouse.y;
                    shell.contextOpen = true;
                } else {
                    shell.contextOpen = false;
                }
            }
        }
    }

    // desktop icons
    Column {
        x: 24
        y: 24
        spacing: 8
        Repeater {
            model: [{ n: "Этот компьютер", c: "#3a7ebf" }, { n: "Корзина", c: "#4d5b6b" },
                    { n: "Проводник", c: "#c9a227" }]
            delegate: Column {
                width: 92
                spacing: 6
                AppTile {
                    width: 40; height: 40
                    baseColor: modelData.c
                    label: modelData.n.substring(0, 1)
                    anchors.horizontalCenter: parent.horizontalCenter
                }
                Text {
                    width: 92
                    horizontalAlignment: Text.AlignHCenter
                    text: modelData.n
                    color: "#ffffff"
                    style: Text.Outline
                    styleColor: "#40000000"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontCaption
                    wrapMode: Text.WordWrap
                }
            }
        }
    }

    // --- window layer (decoration design, see AppWindow.qml) --------------------------------
    AppWindow {
        id: inactiveWindow
        title: "Параметры"
        active: false
        x: 300; y: 150
        width: 520; height: 340
        Item {
            anchors.fill: parent
            Text {
                anchors.centerIn: parent
                text: "Неактивное окно"
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBody
            }
        }
    }

    AppWindow {
        id: activeWindow
        title: "Проводник — Документы"
        active: true
        x: 380; y: 210
        width: 620; height: 400
        Item {
            anchors.fill: parent
            Rectangle {
                id: sidebar
                width: 180
                height: parent.height
                color: Theme.surface
                Column {
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 2
                    Repeater {
                        model: ["Быстрый доступ", "Рабочий стол", "Загрузки", "Документы",
                                "Изображения", "Этот компьютер"]
                        delegate: Item {
                            width: sidebar.width - 16
                            height: 30
                            Rectangle {
                                anchors.fill: parent
                                radius: Theme.radiusSmall
                                color: index === 3 ? Theme.selected : "transparent"
                            }
                            Row {
                                anchors.verticalCenter: parent.verticalCenter
                                anchors.left: parent.left
                                anchors.leftMargin: 8
                                spacing: 10
                                SysIcon {
                                    glyph: "folder"; width: 16; height: 16
                                    color: Theme.textSecondary
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                                Text {
                                    text: modelData
                                    color: Theme.textPrimary
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontCaption + 1
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                            }
                        }
                    }
                }
            }
            Text {
                anchors.centerIn: parent
                anchors.horizontalCenterOffset: 90
                width: 320
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
                text: "Проводник ещё не реализован.\nЭто макет оформления окна, а не рабочее приложение."
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontCaption + 1
            }
        }
    }

    // --- Start -------------------------------------------------------------------------------
    StartMenu {
        id: startMenu
        z: 30
        shown: shell.startOpen
        state: shell.backendState
        system: shell.backendSystem
        apps: shell.backendApps
        installed: shell.backendInstalled
        anchors.horizontalCenter: parent.horizontalCenter
        baseY: shell.height - Theme.taskbarHeight - height - 12
        y: baseY
        onAppLaunched: function(row) {
            shell.backendApps.launchRow(row);
            shell.startOpen = false;
        }
    }

    // --- quick settings ------------------------------------------------------------------------
    QuickSettings {
        id: quickPanel
        z: 30
        shown: shell.quickOpen
        system: shell.backendSystem
        x: shell.width - width - 12
        baseY: shell.height - Theme.taskbarHeight - height - 12
        y: baseY
    }

    // --- context menus --------------------------------------------------------------------------
    ContextMenu {
        id: desktopMenu
        z: 40
        shown: shell.contextOpen
        items: [
            { label: "Вид", glyph: "chevron-right" },
            { label: "Сортировка", glyph: "chevron-right" },
            { label: "Обновить", shortcut: "F5", action: "refresh" },
            { separator: true },
            { label: "Создать", glyph: "folder", action: "new" },
            { label: "Параметры экрана", glyph: "cast", action: "display" },
            { label: "Персонализация", glyph: "brightness", action: "personalize" },
            { separator: true },
            { label: "Открыть терминал", glyph: "chevron-right", action: "terminal" },
            { label: "Показать дополнительные параметры", shortcut: "Shift+F10" }
        ]
        onItemChosen: shell.contextOpen = false
    }

    // --- taskbar ------------------------------------------------------------------------------
    Taskbar {
        id: taskbar
        z: 20
        width: parent.width
        anchors.bottom: parent.bottom
        startActive: shell.startOpen
        quickActive: shell.quickOpen
        activeApp: "Terminal"
        state: shell.backendState
        system: shell.backendSystem
        apps: shell.backendApps
        onStartToggled: { shell.startOpen = !shell.startOpen; shell.quickOpen = false }
        onQuickToggled: { shell.quickOpen = !shell.quickOpen; shell.startOpen = false }
        onAppActivated: function(row) { shell.backendApps.launchRow(row) }
    }
}
