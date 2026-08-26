import QtQuick
import ZaldrosTheme
import "apps"

// Composition root of the Zaldros Shell: desktop, window layer with the two system applications,
// Start, search, quick settings, notification centre, context menus and the taskbar.
// Backends are injected as context properties by zaldros_shell/app.py.
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
    property bool searchOpen: false
    property bool notificationsOpen: false
    property bool contextOpen: false
    property bool lightMode: false

    // --- window manager --------------------------------------------------------------------
    // Two real applications live in the window layer. Each one has open / minimised / maximised
    // state and a z order; the taskbar reflects it and Alt+Tab walks it.
    property var windowIds: ["explorer", "settings"]
    property string focusedWindow: "explorer"
    property var openWindows: ({ explorer: true, settings: true })
    property var minimised: ({ explorer: false, settings: false })
    property var maximised: ({ explorer: false, settings: false })

    function isOpen(id) { return openWindows[id] === true && minimised[id] !== true }
    function focusWindow(id) {
        var next = {};
        for (var key in shell.minimised) next[key] = shell.minimised[key];
        next[id] = false;
        shell.minimised = next;
        shell.openWindows[id] = true;
        shell.focusedWindow = id;
    }
    function setFlag(map, id, value) {
        var next = {};
        for (var key in map) next[key] = map[key];
        next[id] = value;
        return next;
    }
    function toggleWindow(id) {
        if (shell.openWindows[id] !== true) { shell.openWindows = setFlag(shell.openWindows, id, true); shell.focusWindow(id); }
        else if (shell.focusedWindow === id && shell.minimised[id] !== true) shell.minimised = setFlag(shell.minimised, id, true);
        else shell.focusWindow(id);
    }
    function closeAllFlyouts() {
        shell.startOpen = false;
        shell.quickOpen = false;
        shell.searchOpen = false;
        shell.notificationsOpen = false;
        shell.contextOpen = false;
    }

    property var backendState: shellState
    property var backendApps: appModel
    property var backendInstalled: installedModel
    property var backendSystem: systemState
    property var backendFiles: fileModel
    property var backendRecent: recentModel
    property var backendHost: hostInfo

    onLightModeChanged: Theme.dark = !lightMode

    // Global shell keys. KWin runs bare here (no plasmashell), so nothing else in the session owns
    // Meta or Alt+Tab: the shell handles them itself or they do nothing at all.
    focus: true
    Keys.onPressed: function(event) {
        if (event.key === Qt.Key_Super_L || event.key === Qt.Key_Super_R || event.key === Qt.Key_Meta) {
            var open = !shell.startOpen;
            shell.closeAllFlyouts();
            shell.startOpen = open;
            event.accepted = true;
        } else if (event.key === Qt.Key_Escape) {
            shell.closeAllFlyouts();
            event.accepted = true;
        }
    }

    // Tab is consumed by Qt's focus chain before Keys.onPressed sees it, so the switcher has to be
    // a real shortcut rather than a key handler.
    Shortcut {
        sequences: ["Alt+Tab"]
        context: Qt.ApplicationShortcut
        onActivated: {
            var index = shell.windowIds.indexOf(shell.focusedWindow);
            shell.focusWindow(shell.windowIds[(index + 1) % shell.windowIds.length]);
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
                shell.closeAllFlyouts();
                if (mouse.button === Qt.RightButton) {
                    desktopMenu.x = mouse.x;
                    desktopMenu.y = mouse.y;
                    shell.contextOpen = true;
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
            model: [{ n: "Этот компьютер", i: "computer", a: "explorer" },
                    { n: "Корзина", i: "user-trash", a: "" },
                    { n: "Проводник", i: "system-file-manager", a: "explorer" }]
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
                MouseArea {
                    width: 92
                    height: 76
                    y: -76
                    onDoubleClicked: if (modelData.a !== "") shell.focusWindow(modelData.a)
                }
            }
        }
    }

    // --- window layer -------------------------------------------------------------------------
    AppWindow {
        id: settingsWindow
        objectName: "settingsWindow"
        title: "Параметры"
        iconGlyph: "settings"
        visible: shell.isOpen("settings")
        active: shell.focusedWindow === "settings"
        maximized: shell.maximised["settings"] === true
        z: shell.focusedWindow === "settings" ? 12 : 10
        x: maximized ? 0 : 220
        y: maximized ? 0 : 90
        width: maximized ? shell.width : 940
        height: maximized ? shell.height - Theme.taskbarHeight : 620
        onActivateRequested: shell.focusWindow("settings")
        onMinimiseRequested: shell.minimised = shell.setFlag(shell.minimised, "settings", true)
        onMaximiseToggled: shell.maximised = shell.setFlag(shell.maximised, "settings", !maximized)
        onCloseRequested: shell.openWindows = shell.setFlag(shell.openWindows, "settings", false)

        Settings {
            anchors.fill: parent
            host: shell.backendHost
            system: shell.backendSystem
        }
    }

    AppWindow {
        id: explorerWindow
        objectName: "explorerWindow"
        title: "Проводник"
        iconGlyph: "folder"
        showTitleText: false
        tabs: [{ title: shell.backendFiles
                        ? shell.backendFiles.breadcrumbs[shell.backendFiles.breadcrumbs.length - 1].name
                        : "Проводник",
                 glyph: "folder" }]
        visible: shell.isOpen("explorer")
        active: shell.focusedWindow === "explorer"
        maximized: shell.maximised["explorer"] === true
        z: shell.focusedWindow === "explorer" ? 12 : 10
        x: maximized ? 0 : 340
        y: maximized ? 0 : 150
        width: maximized ? shell.width : 1000
        height: maximized ? shell.height - Theme.taskbarHeight : 640
        onActivateRequested: shell.focusWindow("explorer")
        onMinimiseRequested: shell.minimised = shell.setFlag(shell.minimised, "explorer", true)
        onMaximiseToggled: shell.maximised = shell.setFlag(shell.maximised, "explorer", !maximized)
        onCloseRequested: shell.openWindows = shell.setFlag(shell.openWindows, "explorer", false)

        Explorer {
            anchors.fill: parent
            model: shell.backendFiles
        }
    }

    // --- Start ---------------------------------------------------------------------------------
    StartMenu {
        id: startMenu
        z: 30
        shown: shell.startOpen
        state: shell.backendState
        system: shell.backendSystem
        apps: shell.backendApps
        installed: shell.backendInstalled
        recent: shell.backendRecent
        anchors.horizontalCenter: parent.horizontalCenter
        baseY: shell.height - Theme.taskbarHeight - height - Theme.startGap
        y: baseY
        onAppLaunched: function(row) {
            shell.backendApps.launchRow(row);
            shell.startOpen = false;
        }
    }

    // --- search ---------------------------------------------------------------------------------
    SearchFlyout {
        id: searchFlyout
        z: 30
        shown: shell.searchOpen
        installed: shell.backendInstalled
        anchors.horizontalCenter: parent.horizontalCenter
        baseY: shell.height - Theme.taskbarHeight - height - Theme.startGap
        y: baseY
        onAppLaunched: function(row) {
            shell.backendInstalled.launchRow(row);
            shell.searchOpen = false;
        }
    }

    // --- quick settings ----------------------------------------------------------------------------
    QuickSettings {
        id: quickPanel
        objectName: "quickPanel"
        z: 30
        shown: shell.quickOpen
        system: shell.backendSystem
        x: shell.width - width - Theme.flyoutGap
        baseY: shell.height - Theme.taskbarHeight - height - Theme.flyoutGap
        y: baseY
    }

    // --- notification centre -------------------------------------------------------------------------
    NotificationCenter {
        id: notificationCentre
        z: 30
        shown: shell.notificationsOpen
        x: shell.width - width - Theme.flyoutGap
        baseY: shell.height - Theme.taskbarHeight - height - Theme.flyoutGap
        y: baseY
    }

    // --- context menus ----------------------------------------------------------------------------------
    ContextMenu {
        id: desktopMenu
        objectName: "contextMenu"
        z: 40
        shown: shell.contextOpen
        items: [
            { label: "Вид", glyph: "grid", submenu: true },
            { label: "Сортировка", glyph: "sort", submenu: true },
            { label: "Обновить", glyph: "refresh", shortcut: "F5", action: "refresh" },
            { separator: true },
            { label: "Создать", glyph: "add-circle", submenu: true },
            { label: "Параметры экрана", glyph: "desktop", action: "display" },
            { label: "Персонализация", glyph: "paint-brush", action: "personalize" },
            { separator: true },
            { label: "Открыть терминал", glyph: "list", action: "terminal" },
            { label: "Показать дополнительные параметры", glyph: "more", shortcut: "Shift+F10" }
        ]
        onItemChosen: function(action) {
            shell.contextOpen = false;
            if (action === "display") { shell.focusWindow("settings"); }
            else if (action === "personalize") { shell.focusWindow("settings"); }
        }
    }

    // --- taskbar ------------------------------------------------------------------------------------
    Taskbar {
        id: taskbar
        z: 20
        width: parent.width
        anchors.bottom: parent.bottom
        startActive: shell.startOpen
        quickActive: shell.quickOpen
        searchActive: shell.searchOpen
        notificationsActive: shell.notificationsOpen
        windowButtons: [
            { id: "explorer", name: "Проводник", glyph: "folder",
              running: shell.openWindows["explorer"] === true,
              active: shell.focusedWindow === "explorer" && shell.isOpen("explorer") },
            { id: "settings", name: "Параметры", glyph: "settings",
              running: shell.openWindows["settings"] === true,
              active: shell.focusedWindow === "settings" && shell.isOpen("settings") }
        ]
        state: shell.backendState
        system: shell.backendSystem
        apps: shell.backendApps
        onStartToggled: { var open = !shell.startOpen; shell.closeAllFlyouts(); shell.startOpen = open }
        onSearchToggled: { var open = !shell.searchOpen; shell.closeAllFlyouts(); shell.searchOpen = open }
        onQuickToggled: { var open = !shell.quickOpen; shell.closeAllFlyouts(); shell.quickOpen = open }
        onNotificationsToggled: { var open = !shell.notificationsOpen; shell.closeAllFlyouts(); shell.notificationsOpen = open }
        onTaskViewToggled: shell.focusWindow(shell.focusedWindow === "explorer" ? "settings" : "explorer")
        onAppActivated: function(row) { shell.backendApps.launchRow(row) }
        onWindowActivated: function(id) { shell.toggleWindow(id) }
    }

}
