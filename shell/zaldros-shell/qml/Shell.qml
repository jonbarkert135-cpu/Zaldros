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
    property int settingsPage: 1        // rail index the renderer opens Settings on
    property bool quickOpen: false
    property bool searchOpen: false
    property bool notificationsOpen: false
    property bool clipboardOpen: false
    property bool gameBarOpen: false
    property bool gameBarCaptureOpen: true       // the capture widget is the one Windows pins by default
    property bool gameBarPerformanceOpen: false
    property bool contextOpen: false
    property bool lightMode: false

    // --- window manager --------------------------------------------------------------------
    // Two real applications live in the window layer. Each one has open / minimised / maximised
    // state and a z order; the taskbar reflects it and Alt+Tab walks it.
    property var windowIds: ["explorer", "settings", "taskmanager", "devicemanager", "terminal"]
    property string focusedWindow: "explorer"
    property var openWindows: ({ explorer: true, settings: true, taskmanager: false, devicemanager: false, terminal: false })
    property var minimised: ({ explorer: false, settings: false, taskmanager: false, devicemanager: false, terminal: false })
    property var maximised: ({ explorer: false, settings: false, taskmanager: false, devicemanager: false, terminal: false })

    // Snap layouts. A snapped window keeps a zone — fractions of the work area — instead of its
    // designed geometry; maximising or snapping again replaces it, restoring clears it.
    property var snapped: ({})
    property bool snapOpen: false
    property string snapTarget: ""
    property real snapAnchorX: 0
    property real snapAnchorY: 0
    // The snap bar at the top edge: which window is being dragged up there, if any.
    property bool snapBarOpen: false
    property string snapBarTarget: ""

    function isOpen(id) { return openWindows[id] === true && minimised[id] !== true }
    function windowItem(id) {
        if (id === "settings") return settingsWindow;
        if (id === "explorer") return explorerWindow;
        if (id === "taskmanager") return taskManagerWindow;
        if (id === "terminal") return terminalWindow;
        if (id === "devicemanager") return deviceManagerWindow;
        return null;
    }

    function openSnapMenu(id, anchorX, anchorY) {
        shell.snapTarget = id;
        shell.snapAnchorX = anchorX;
        shell.snapAnchorY = anchorY;
        shell.snapOpen = true;
    }
    // Reported by a window that is being dragged: at the top edge the bar drops down, away from it
    // the bar goes away again — but only for the window that opened it.
    function requestSnapBar(id, atTopEdge) {
        if (atTopEdge) {
            shell.snapBarTarget = id;
            shell.snapBarOpen = true;
        } else if (shell.snapBarTarget === id) {
            shell.snapBarOpen = false;
        }
    }
    // Called by the flyout and, in renders and tests, directly: layout/zone indices in, geometry out.
    function applySnap(id, zone) {
        shell.maximised = shell.setFlag(shell.maximised, id, false);
        var next = {};
        for (var key in shell.snapped) next[key] = shell.snapped[key];
        next[id] = zone;
        shell.snapped = next;
        shell.snapOpen = false;
        shell.snapBarOpen = false;
        shell.focusWindow(id);
    }
    function clearSnap(id) {
        var next = {};
        for (var key in shell.snapped) if (key !== id) next[key] = shell.snapped[key];
        shell.snapped = next;
    }
    // Window geometry, in one place: a snapped zone wins, then maximised, then the designed size.
    function winX(id, x, w) {
        var zone = shell.snapped[id];
        if (zone) return Math.round(zone.x * shell.workWidth);
        return shell.maximised[id] === true ? 0 : shell.placedX(x, w);
    }
    function winY(id, y, h) {
        var zone = shell.snapped[id];
        if (zone) return Math.round(zone.y * shell.workHeight);
        return shell.maximised[id] === true ? 0 : shell.placedY(y, h);
    }
    function winWidth(id, w) {
        var zone = shell.snapped[id];
        if (zone) return Math.round(zone.w * shell.workWidth);
        return shell.maximised[id] === true ? shell.width : shell.placedWidth(w);
    }
    function winHeight(id, h) {
        var zone = shell.snapped[id];
        if (zone) return Math.round(zone.h * shell.workHeight);
        return shell.maximised[id] === true ? shell.workHeight : shell.placedHeight(h);
    }
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
    // Window placement. The design canvas is 1280x1000; a real screen is often shorter (the ISO
    // boots at 1280x800) and run #29 caught the Explorer window hanging 60 px off the right edge
    // with its search field and caption buttons cut off. Keep the designed offset when the window
    // fits, otherwise shrink it to the work area and centre it, which is what Windows does with a
    // window that cannot be placed where it was asked for.
    readonly property int workWidth: shell.width
    readonly property int workHeight: shell.height - Theme.taskbarHeight
    function placedWidth(w) { return Math.min(w, shell.workWidth) }
    function placedHeight(h) { return Math.min(h, shell.workHeight) }
    function placedX(x, w) {
        var ww = shell.placedWidth(w);
        return (x + ww <= shell.workWidth) ? x : Math.round((shell.workWidth - ww) / 2);
    }
    function placedY(y, h) {
        var hh = shell.placedHeight(h);
        return (y + hh <= shell.workHeight) ? y : Math.round((shell.workHeight - hh) / 2);
    }

    function closeAllFlyouts() {
        shell.snapOpen = false;
        shell.snapBarOpen = false;
        shell.startOpen = false;
        shell.quickOpen = false;
        shell.searchOpen = false;
        shell.notificationsOpen = false;
        shell.clipboardOpen = false;
        shell.gameBarOpen = false;
        shell.contextOpen = false;
    }

    property var backendState: shellState
    property var backendApps: appModel
    property var backendInstalled: installedModel
    property var backendSystem: systemState
    property var backendWeather: weatherState
    property var backendFiles: fileModel
    property var backendRecent: recentModel
    property var backendHost: hostInfo
    property var backendClipboard: clipboardModel
    property var backendCapture: gameBarModel
    property var backendProcesses: processModel
    property var backendStartup: startupModel
    property var backendDevices: deviceModel
    property var backendTerminal: terminalModel

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
    // Win+V. Qt delivers this while the desktop has focus; a session-wide Meta+V needs the same
    // global-shortcut path as Alt+Tab and is wired once that path has a passing boot verdict.
    Shortcut {
        sequences: ["Meta+V"]
        context: Qt.ApplicationShortcut
        onActivated: {
            var open = !shell.clipboardOpen;
            shell.closeAllFlyouts();
            shell.clipboardOpen = open;
        }
    }

    // Win+G — the capture widget. Same story as Win+V: application-wide today, session-wide once
    // the global-shortcut path has a passing boot verdict.
    Shortcut {
        sequences: ["Meta+G"]
        context: Qt.ApplicationShortcut
        onActivated: {
            var open = !shell.gameBarOpen;
            shell.closeAllFlyouts();
            shell.gameBarOpen = open;
        }
    }

    Shortcut {
        sequences: ["Alt+Tab"]
        context: Qt.ApplicationShortcut
        onActivated: {
            // Only windows that are actually open take part: Alt+Tab must never *launch* the
            // Task Manager, which is what cycling the full id list would do.
            var live = shell.windowIds.filter(function (id) { return shell.openWindows[id] === true });
            if (live.length === 0)
                return;
            var index = live.indexOf(shell.focusedWindow);
            shell.focusWindow(live[(index + 1) % live.length]);
            shell.startOpen = false;
        }
    }

    // Win+Z — snap layouts for the focused window, anchored where its maximise button is.
    Shortcut {
        sequences: ["Meta+Z"]
        context: Qt.ApplicationShortcut
        onActivated: {
            if (shell.snapOpen) { shell.snapOpen = false; return }
            var id = shell.focusedWindow;
            if (!shell.isOpen(id))
                return;
            var item = shell.windowItem(id);
            if (item === null)
                return;
            shell.closeAllFlyouts();
            // The maximise button is the middle of the three caption buttons on the right edge.
            shell.openSnapMenu(id, item.x + item.width - Theme.captionWidth * 1.5,
                               item.y + item.barHeight);
        }
    }

    // Ctrl+Shift+Esc — the Windows shortcut, opening the Task Manager and focusing it.
    Shortcut {
        sequences: ["Ctrl+Shift+Escape"]
        context: Qt.ApplicationShortcut
        onActivated: {
            shell.closeAllFlyouts();
            shell.openWindows = shell.setFlag(shell.openWindows, "taskmanager", true);
            shell.focusWindow("taskmanager");
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
        showIcon: false                       // Windows 11 Settings shows no icon, only the arrow
        showBack: true
        onBackRequested: settingsApp.goBack()
        visible: shell.isOpen("settings")
        active: shell.focusedWindow === "settings"
        maximized: shell.maximised["settings"] === true
        snapped: shell.snapped["settings"] !== undefined
        z: shell.focusedWindow === "settings" ? 12 : 10
        x: shell.winX("settings", 220, 940)
        y: shell.winY("settings", 90, 620)
        width: shell.winWidth("settings", 940)
        height: shell.winHeight("settings", 620)
        onActivateRequested: shell.focusWindow("settings")
        onMinimiseRequested: shell.minimised = shell.setFlag(shell.minimised, "settings", true)
        onMaximiseToggled: {
            shell.clearSnap("settings");
            shell.maximised = shell.setFlag(shell.maximised, "settings", !maximized);
        }
        onSnapBarRequested: function (atTopEdge) {
            shell.requestSnapBar("settings", atTopEdge);
        }
        onSnapMenuRequested: function (anchorX, anchorY) {
            shell.openSnapMenu("settings", anchorX, anchorY);
        }
        onCloseRequested: shell.openWindows = shell.setFlag(shell.openWindows, "settings", false)

        Settings {
            id: settingsApp
            anchors.fill: parent
            host: shell.backendHost
            system: shell.backendSystem
            tree: settingsTree
            page: shell.settingsPage
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
        snapped: shell.snapped["explorer"] !== undefined
        z: shell.focusedWindow === "explorer" ? 12 : 10
        x: shell.winX("explorer", 340, 1000)
        y: shell.winY("explorer", 150, 640)
        width: shell.winWidth("explorer", 1000)
        height: shell.winHeight("explorer", 640)
        onActivateRequested: shell.focusWindow("explorer")
        onMinimiseRequested: shell.minimised = shell.setFlag(shell.minimised, "explorer", true)
        onMaximiseToggled: {
            shell.clearSnap("explorer");
            shell.maximised = shell.setFlag(shell.maximised, "explorer", !maximized);
        }
        onSnapBarRequested: function (atTopEdge) {
            shell.requestSnapBar("explorer", atTopEdge);
        }
        onSnapMenuRequested: function (anchorX, anchorY) {
            shell.openSnapMenu("explorer", anchorX, anchorY);
        }
        onCloseRequested: shell.openWindows = shell.setFlag(shell.openWindows, "explorer", false)

        Explorer {
            anchors.fill: parent
            model: shell.backendFiles
        }
    }

    // Ctrl+Shift+Esc, as in Windows. Closed by default: a Task Manager nobody opened must not
    // change a single pixel of the desktop, and must not read /proc either.
    AppWindow {
        id: taskManagerWindow
        objectName: "taskManagerWindow"
        title: "Диспетчер задач"
        iconGlyph: "apps"
        visible: shell.isOpen("taskmanager")
        active: shell.focusedWindow === "taskmanager"
        maximized: shell.maximised["taskmanager"] === true
        snapped: shell.snapped["taskmanager"] !== undefined
        z: shell.focusedWindow === "taskmanager" ? 12 : 10
        x: shell.winX("taskmanager", 300, 1020)
        y: shell.winY("taskmanager", 120, 660)
        width: shell.winWidth("taskmanager", 1020)
        height: shell.winHeight("taskmanager", 660)
        onActivateRequested: shell.focusWindow("taskmanager")
        onMinimiseRequested: shell.minimised = shell.setFlag(shell.minimised, "taskmanager", true)
        onMaximiseToggled: {
            shell.clearSnap("taskmanager");
            shell.maximised = shell.setFlag(shell.maximised, "taskmanager", !maximized);
        }
        onSnapBarRequested: function (atTopEdge) {
            shell.requestSnapBar("taskmanager", atTopEdge);
        }
        onSnapMenuRequested: function (anchorX, anchorY) {
            shell.openSnapMenu("taskmanager", anchorX, anchorY);
        }
        onCloseRequested: shell.openWindows = shell.setFlag(shell.openWindows, "taskmanager", false)

        TaskManager {
            anchors.fill: parent
            model: shell.backendProcesses
            startup: shell.backendStartup
        }
    }

    // Zaldros Terminal. Closed by default; opening it starts one real shell on a pty.
    AppWindow {
        id: terminalWindow
        objectName: "terminalWindow"
        title: "Командная строка"
        iconGlyph: "terminal"
        // One bar, like the real thing: the tabs, the «+» and the profile caret sit in the
        // title bar itself, next to the caption buttons.
        tabs: shell.backendTerminal
              ? shell.backendTerminal.tabs.map(function (tab) {
                    return { title: tab.name, glyph: "terminal", active: tab.active };
                })
              : []
        showTabMenu: true
        onTabActivated: function (index) { shell.backendTerminal.selectTab(index) }
        onTabCloseRequested: function (index) { shell.backendTerminal.closeTab(index) }
        onNewTabRequested: shell.backendTerminal.openTab("")
        onTabMenuRequested: terminalPane.dropdownOpen = !terminalPane.dropdownOpen
        visible: shell.isOpen("terminal")
        active: shell.focusedWindow === "terminal"
        maximized: shell.maximised["terminal"] === true
        snapped: shell.snapped["terminal"] !== undefined
        z: shell.focusedWindow === "terminal" ? 12 : 10
        x: shell.winX("terminal", 360, 980)
        y: shell.winY("terminal", 170, 600)
        width: shell.winWidth("terminal", 980)
        height: shell.winHeight("terminal", 600)
        onActivateRequested: shell.focusWindow("terminal")
        onMinimiseRequested: shell.minimised = shell.setFlag(shell.minimised, "terminal", true)
        onMaximiseToggled: {
            shell.clearSnap("terminal");
            shell.maximised = shell.setFlag(shell.maximised, "terminal", !maximized);
        }
        onSnapBarRequested: function (atTopEdge) {
            shell.requestSnapBar("terminal", atTopEdge);
        }
        onSnapMenuRequested: function (anchorX, anchorY) {
            shell.openSnapMenu("terminal", anchorX, anchorY);
        }
        onCloseRequested: {
            shell.openWindows = shell.setFlag(shell.openWindows, "terminal", false);
            // Closing the window kills the shells it owns: an invisible pty is a leak, and a
            // background bash nobody can see is exactly what the performance rule forbids.
            if (shell.backendTerminal) shell.backendTerminal.closeAll();
        }

        Terminal {
            id: terminalPane
            anchors.fill: parent
            model: shell.backendTerminal
        }
    }

    // «Диспетчер устройств». Closed by default, like the Task Manager: an unopened window may
    // not change a pixel of the desktop and may not touch sysfs.
    AppWindow {
        id: deviceManagerWindow
        objectName: "deviceManagerWindow"
        title: "Диспетчер устройств"
        iconGlyph: "apps"
        visible: shell.isOpen("devicemanager")
        active: shell.focusedWindow === "devicemanager"
        maximized: shell.maximised["devicemanager"] === true
        snapped: shell.snapped["devicemanager"] !== undefined
        z: shell.focusedWindow === "devicemanager" ? 12 : 10
        x: shell.winX("devicemanager", 280, 1040)
        y: shell.winY("devicemanager", 110, 640)
        width: shell.winWidth("devicemanager", 1040)
        height: shell.winHeight("devicemanager", 640)
        onActivateRequested: shell.focusWindow("devicemanager")
        onMinimiseRequested: shell.minimised = shell.setFlag(shell.minimised, "devicemanager", true)
        onMaximiseToggled: {
            shell.clearSnap("devicemanager");
            shell.maximised = shell.setFlag(shell.maximised, "devicemanager", !maximized);
        }
        onSnapBarRequested: function (atTopEdge) {
            shell.requestSnapBar("devicemanager", atTopEdge);
        }
        onSnapMenuRequested: function (anchorX, anchorY) {
            shell.openSnapMenu("devicemanager", anchorX, anchorY);
        }
        onCloseRequested: shell.openWindows = shell.setFlag(shell.openWindows, "devicemanager", false)

        DeviceManager {
            anchors.fill: parent
            model: shell.backendDevices
        }
    }

    Connections {
        target: deviceManagerWindow
        function onVisibleChanged() {
            // Enumerating happens when the window opens. Hardware changes rarely and udev will
            // announce it; a timer here would be exactly the polling ADR-0014 removed.
            if (deviceManagerWindow.visible && shell.backendDevices) shell.backendDevices.refresh();
        }
    }

    // Sampling follows the window: open means a 2 s refresh, closed means no /proc reads at all.
    Connections {
        target: taskManagerWindow
        function onVisibleChanged() {
            if (shell.backendProcesses) shell.backendProcesses.setActive(taskManagerWindow.visible);
            if (taskManagerWindow.visible && shell.backendStartup) shell.backendStartup.refresh();
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

    // --- snap layouts ------------------------------------------------------------------------------
    // Opens under the maximise button of the window that asked for it (Win+Z uses the focused one)
    // and stays inside the screen, which is what Windows does near the right edge.
    SnapLayouts {
        id: snapFlyout
        objectName: "snapFlyout"
        z: 40
        visible: shell.snapOpen
        x: Math.max(Theme.flyoutGap,
                    Math.min(shell.snapAnchorX - width / 2,
                             shell.width - width - Theme.flyoutGap))
        y: Math.min(shell.snapAnchorY + 8, shell.workHeight - height - Theme.flyoutGap)
        onZoneChosen: function (layout, zone, zoneRect) {
            shell.applySnap(shell.snapTarget, zoneRect);
        }
    }

    // --- snap bar ---------------------------------------------------------------------------------
    // Hangs from the top edge, centred, while a window is dragged up there.
    SnapBar {
        id: snapBar
        objectName: "snapBar"
        z: 40
        visible: shell.snapBarOpen
        x: Math.round((shell.width - width) / 2)
        y: Theme.flyoutGap
        onZoneChosen: function (layout, zone, zoneRect) {
            shell.applySnap(shell.snapBarTarget, zoneRect);
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

    // --- clipboard history (Win+V) --------------------------------------------------------------
    ClipboardFlyout {
        id: clipboardFlyout
        z: 30
        shown: shell.clipboardOpen
        clipboard: shell.backendClipboard
        x: Theme.flyoutGap
        baseY: shell.height - Theme.taskbarHeight - height - Theme.flyoutGap
        y: baseY
    }

    // --- game bar (Win+G) -------------------------------------------------------------------------
    // Windows shows two things at once: the floating bar at the top of the screen, and whichever
    // widgets are pinned under it. Ours does the same — the bar owns the widgets, the capture
    // widget is one of them, and the camera button on the bar lights up while it is open.
    GameBarToolbar {
        id: gameBarToolbar
        z: 31
        shown: shell.gameBarOpen
        state: shell.backendState
        system: shell.backendSystem
        capture: shell.backendCapture
        captureActive: shell.gameBarCaptureOpen
        performanceActive: shell.gameBarPerformanceOpen
        x: (shell.width - width) / 2
        y: Theme.flyoutGap
        onCaptureToggled: shell.gameBarCaptureOpen = !shell.gameBarCaptureOpen
        onPerformanceToggled: shell.gameBarPerformanceOpen = !shell.gameBarPerformanceOpen
        onSettingsRequested: shell.focusWindow("settings")
    }

    GameBarFlyout {
        id: gameBarFlyout
        z: 30
        shown: shell.gameBarOpen && shell.gameBarCaptureOpen
        capture: shell.backendCapture
        x: Theme.flyoutGap
        y: Theme.flyoutGap
        onCloseRequested: shell.gameBarCaptureOpen = false
    }

    GameBarPerformance {
        id: gameBarPerformance
        z: 30
        shown: shell.gameBarOpen && shell.gameBarPerformanceOpen
        state: shell.backendState
        x: shell.width - width - Theme.flyoutGap
        y: Theme.flyoutGap + Theme.gameBarBarHeight + Theme.flyoutGap
        onCloseRequested: shell.gameBarPerformanceOpen = false
    }

    // --- context menus ----------------------------------------------------------------------------------
    ContextMenu {
        id: desktopMenu
        objectName: "contextMenu"
        z: 40
        shown: shell.contextOpen
        items: [
            { label: "Вид", glyph: "grid", submenu: true, children: [
                { label: "Крупные значки", action: "view-large" },
                { label: "Обычные значки", action: "view-medium" },
                { label: "Мелкие значки", action: "view-small" },
                { separator: true },
                { label: "Упорядочить значки автоматически", action: "view-auto" }
            ] },
            { label: "Сортировка", glyph: "sort", submenu: true, children: [
                { label: "Имя", action: "sort-name" },
                { label: "Размер", action: "sort-size" },
                { label: "Тип элемента", action: "sort-type" },
                { label: "Дата изменения", action: "sort-date" }
            ] },
            { label: "Обновить", glyph: "refresh", shortcut: "F5", action: "refresh" },
            { separator: true },
            { label: "Создать", glyph: "add-circle", submenu: true, children: [
                { label: "Папку", glyph: "folder", action: "new-folder" },
                { label: "Текстовый документ", glyph: "document", action: "new-text" }
            ] },
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
        ].concat(shell.openWindows["taskmanager"] === true
                 // A taskbar button appears only while the Task Manager runs — Explorer and
                 // Settings are pinned, this one is not, so the closed desktop is pixel-identical.
                 ? [{ id: "taskmanager", name: "Диспетчер задач", glyph: "apps", running: true,
                      active: shell.focusedWindow === "taskmanager" && shell.isOpen("taskmanager") }]
                 : []).concat(shell.openWindows["terminal"] === true
                 ? [{ id: "terminal", name: "Командная строка", glyph: "terminal", running: true,
                      active: shell.focusedWindow === "terminal" && shell.isOpen("terminal") }]
                 : []).concat(shell.openWindows["devicemanager"] === true
                 ? [{ id: "devicemanager", name: "Диспетчер устройств", glyph: "apps", running: true,
                      active: shell.focusedWindow === "devicemanager" && shell.isOpen("devicemanager") }]
                 : [])
        state: shell.backendState
        system: shell.backendSystem
        apps: shell.backendApps
        weather: shell.backendWeather
        onStartToggled: { var open = !shell.startOpen; shell.closeAllFlyouts(); shell.startOpen = open }
        onSearchToggled: { var open = !shell.searchOpen; shell.closeAllFlyouts(); shell.searchOpen = open }
        onQuickToggled: { var open = !shell.quickOpen; shell.closeAllFlyouts(); shell.quickOpen = open }
        onNotificationsToggled: { var open = !shell.notificationsOpen; shell.closeAllFlyouts(); shell.notificationsOpen = open }
        onTaskViewToggled: shell.focusWindow(shell.focusedWindow === "explorer" ? "settings" : "explorer")
        onAppActivated: function(row) { shell.backendApps.launchRow(row) }
        onWindowActivated: function(id) { shell.toggleWindow(id) }
    }

}
