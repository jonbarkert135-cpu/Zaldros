import QtQuick
import ZaldrosTheme

// Composition root of the Zaldros Shell: desktop, window layer, Start, quick settings, context
// menus and the taskbar. Backends are injected as properties by zaldros_shell/app.py.
Item {
    id: shell

    Component.onCompleted: {
        Theme.fontFamily = uiFontFamily;   // real family, resolved by the Python side
        Theme.wallpaper = wallpaperUrl;
    }

    width: 1600
    height: 1000

    property bool startOpen: false
    property bool quickOpen: false
    property bool contextOpen: false
    property bool lightMode: false
    // Which of the two window-layer surfaces holds focus. Alt+Tab flips it, exactly like the
    // Windows 11 switcher does with two open windows.
    property int focusedWindow: 1

    // Global shell keys. KWin runs bare here (no plasmashell), so nothing else in the session
    // owns Meta or Alt+Tab: the shell has to handle them itself or they do nothing at all.
    // Run #25 proved that: every host-injected keystroke left the frame byte-identical.
    focus: true
    Keys.onPressed: function(event) {
        if (event.key === Qt.Key_Super_L || event.key === Qt.Key_Super_R || event.key === Qt.Key_Meta) {
            shell.startOpen = !shell.startOpen;
            shell.quickOpen = false;
            shell.contextOpen = false;
            event.accepted = true;
        } else if (event.key === Qt.Key_Tab && (event.modifiers & Qt.AltModifier)) {
            shell.focusedWindow = shell.focusedWindow === 0 ? 1 : 0;
            shell.startOpen = false;
            event.accepted = true;
        } else if (event.key === Qt.Key_Escape) {
            shell.startOpen = false;
            shell.quickOpen = false;
            shell.contextOpen = false;
            event.accepted = true;
        }
    }
    property var backendState: shellState
    property var backendApps: appModel
    property var backendInstalled: installedModel
    property var backendSystem: systemState

    onLightModeChanged: Theme.dark = !lightMode

    // Tab is consumed by Qt's focus chain before Keys.onPressed sees it, so the switcher binding
    // has to be a real shortcut rather than a key handler.
    Shortcut {
        sequences: ["Alt+Tab"]
        context: Qt.ApplicationShortcut
        onActivated: {
            shell.focusedWindow = shell.focusedWindow === 0 ? 1 : 0;
            shell.startOpen = false;
        }
    }

    // --- desktop ---------------------------------------------------------------------------
    Rectangle {
        anchors.fill: parent
        color: Theme.dark ? "#08192c" : "#2d5b8f"

        // Zaldros wallpaper — our own artwork (assets/wallpaper/generate.py), never a Microsoft file.
        Image {
            anchors.fill: parent
            source: Theme.wallpaper
            asynchronous: false
            fillMode: Image.PreserveAspectCrop
            opacity: Theme.dark ? 1.0 : 0.85
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
            model: [{ n: "Этот компьютер", i: "computer" },
                    { n: "Корзина", i: "user-trash" },
                    { n: "Проводник", i: "system-file-manager" }]
            delegate: Column {
                width: 92
                spacing: 6
                Image {
                    width: 48; height: 48
                    anchors.horizontalCenter: parent.horizontalCenter
                    source: "image://zaldrosicon/app/" + modelData.i
                    sourceSize.width: 96; sourceSize.height: 96
                    asynchronous: false
                    fillMode: Image.PreserveAspectFit
                    smooth: true
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
        active: shell.focusedWindow === 0
        z: shell.focusedWindow === 0 ? 11 : 10
        x: 300; y: 150
        width: 520; height: 340
        Item {
            anchors.fill: parent
            Text {
                anchors.centerIn: parent
                text: inactiveWindow.active ? "Параметры" : "Неактивное окно"
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBody
            }
        }
    }

    AppWindow {
        id: activeWindow
        title: "Проводник — Документы"
        active: shell.focusedWindow === 1
        z: shell.focusedWindow === 1 ? 11 : 10
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
                        // Sidebar entries carry the freedesktop icon name; the artwork comes from
                        // the Win11 icon theme (GPL-3), never from hand-drawn strokes.
                        model: [{ t: "Быстрый доступ", i: "user-home" },
                                { t: "Рабочий стол", i: "user-desktop" },
                                { t: "Загрузки", i: "folder-download" },
                                { t: "Документы", i: "folder-documents" },
                                { t: "Изображения", i: "folder-pictures" },
                                { t: "Этот компьютер", i: "computer" }]
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
                                Image {
                                    width: 18; height: 18
                                    source: "image://zaldrosicon/app/" + modelData.i
                                    sourceSize.width: 36; sourceSize.height: 36
                                    asynchronous: false
                                    fillMode: Image.PreserveAspectFit
                                    smooth: true
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                                Text {
                                    text: modelData.t
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
