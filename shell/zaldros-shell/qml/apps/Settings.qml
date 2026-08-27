import QtQuick
import QtQuick.Controls
import ZaldrosTheme
import ".."

// Zaldros Settings, laid out to the measured Windows 11 Settings capture
// (assets/refs/win11_settings_system.png): 320 px navigation rail with the account card and a
// search field, a large page title, and stacked 74 px cards on the right.
//
// Every value on the System and About pages is read from this machine (hostinfo.py). A reading the
// system cannot provide shows an em-free dash, never a filler string.
Item {
    id: settings
    property var host: null
    property var system: null
    property var tree: null
    // `page` stays an index into the rail so the renderer and the UI test can select a category;
    // `stack` is the nested path inside it, exactly like the back arrow in Windows 11 Settings.
    property int page: 0
    property var stack: []
    property var railItems: tree ? tree.rail : []
    readonly property string currentId: stack.length > 0 ? stack[stack.length - 1]
                                        : (railItems && railItems.length > page ? railItems[page].id : "home")
    // page() is a slot, not a property, so nothing would re-read it after a switch was flipped:
    // the revision counter is what makes the row redraw with the value that was just stored.
    property int treeRevision: 0
    readonly property var current: (treeRevision, tree ? tree.page(currentId)
                                                       : ({ title: "", entries: [] }))

    function reloadTree() {
        if (settings.tree) settings.tree.refresh();
        settings.treeRevision += 1;
    }

    function openPage(id) { var next = stack.slice(); next.push(id); stack = next }
    function goBack() { var next = stack.slice(); next.pop(); stack = next }
    function selectRail(index) { page = index; stack = [] }


    function reading(key) {
        var value = settings.host ? settings.host.value(key) : "";
        return value === "" ? "–" : value;
    }

    Rectangle { anchors.fill: parent; color: Theme.appBackground }

    // --- navigation rail --------------------------------------------------------------------
    Item {
        id: rail
        objectName: "settingsRail"
        width: 320
        height: parent.height

        // account card
        Row {
            id: account
            x: 24
            y: 16
            spacing: 12
            Rectangle {
                width: 48; height: 48; radius: 24
                color: Theme.surfaceElevated
                SysIcon {
                    anchors.centerIn: parent
                    glyph: "person"; width: 24; height: 24
                    color: Theme.textSecondary
                }
            }
            Column {
                anchors.verticalCenter: parent.verticalCenter
                spacing: 2
                Text {
                    text: settings.system && settings.system.userName ? settings.system.userName : "пользователь"
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBody
                }
                Text {
                    text: settings.reading("deviceName")
                    color: Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontCaption
                }
            }
        }

        Rectangle {
            id: navSearch
            x: 24
            anchors.top: account.bottom
            anchors.topMargin: 20
            width: rail.width - 48
            height: 32
            radius: Theme.radiusSmall
            color: Theme.dark ? "#1f1f1f" : "#ffffff"
            border.width: 1
            border.color: Theme.border
            Text {
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                anchors.leftMargin: 10
                text: "Найти параметр"
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontCaption
            }
            SysIcon {
                anchors.verticalCenter: parent.verticalCenter
                anchors.right: parent.right
                anchors.rightMargin: 10
                glyph: "search"; width: 14; height: 14
                color: Theme.textSecondary
            }
        }

        Column {
            anchors.top: navSearch.bottom
            anchors.topMargin: 12
            x: 12
            spacing: 2
            Repeater {
                model: settings.railItems
                delegate: Rectangle {
                    width: rail.width - 24
                    height: 36
                    radius: Theme.radiusSmall
                    color: settings.page === index ? Theme.selected
                           : (navArea.containsMouse ? Theme.hover : "transparent")
                    // Windows marks the active page with an accent bar on the left edge
                    Rectangle {
                        visible: settings.page === index
                        anchors.verticalCenter: parent.verticalCenter
                        x: 2
                        width: 3; height: 16; radius: 1.5
                        color: Theme.accent
                    }
                    Row {
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.left: parent.left
                        anchors.leftMargin: 14
                        spacing: 12
                        SysIcon {
                            glyph: modelData.glyph
                            width: 16; height: 16
                            color: settings.page === index ? Theme.accent : Theme.textPrimary
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Text {
                            text: modelData.title
                            color: Theme.textPrimary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontCaption + 1
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }
                    MouseArea {
                        id: navArea
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: settings.selectRail(index)
                    }
                }
            }
        }
    }

    // --- page body -----------------------------------------------------------------------------
    Flickable {
        id: body
        objectName: "settingsBody"
        anchors.left: rail.right
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        contentHeight: pageColumn.implicitHeight + 48
        clip: true
        ScrollBar.vertical: ScrollBar { }

        Column {
            id: pageColumn
            x: 32
            y: 24
            width: body.width - 96
            spacing: 16

            // back arrow, shown only inside a nested page
            Row {
                spacing: 12
                Rectangle {
                    visible: settings.stack.length > 0
                    width: 32; height: 32; radius: Theme.radiusSmall
                    color: backArea.containsMouse ? Theme.hover : "transparent"
                    SysIcon {
                        anchors.centerIn: parent
                        glyph: "arrow-left"; width: 16; height: 16
                        color: Theme.textPrimary
                    }
                    MouseArea {
                        id: backArea
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: settings.goBack()
                    }
                }
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: settings.current.title
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontPageTitle
                    font.weight: Font.DemiBold
                }
            }

            // device banner, shown on Главная / Система / О системе like Windows does
            Row {
                visible: settings.currentId === "home" || settings.currentId === "system"
                         || settings.currentId === "about"
                spacing: 20
                Rectangle {
                    width: 124; height: 76
                    radius: Theme.radiusSmall
                    color: Theme.surface
                    clip: true
                    Image {
                        anchors.fill: parent
                        source: Theme.wallpaper
                        fillMode: Image.PreserveAspectCrop
                        asynchronous: false
                    }
                }
                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 4
                    Text {
                        text: settings.reading("deviceName")
                        color: Theme.textPrimary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSubtitle
                        font.weight: Font.DemiBold
                    }
                    Text {
                        text: settings.reading("cpuModel")
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontCaption
                    }
                    Text {
                        text: settings.reading("osName")
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontCaption
                    }
                }
            }

            // page cards
            Repeater {
                model: settings.current.entries
                delegate: Column {
                    width: pageColumn.width
                    spacing: 8
                    // Windows breaks long pages into named sections; ours carries the same headings
                    Text {
                        visible: modelData.group !== ""
                        text: modelData.group
                        color: Theme.textPrimary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBody
                        font.weight: Font.DemiBold
                        topPadding: index === 0 ? 0 : 12
                    }
                    SettingsCard {
                    width: parent.width
                    glyph: modelData.glyph
                    title: modelData.title
                    detail: modelData.subtitle
                    value: modelData.value
                    hasToggle: modelData.hasToggle
                    toggled: modelData.toggle
                    // A control the machine cannot honour is drawn dimmed with its reason in the
                    // value column, the way Windows greys a setting it cannot apply.
                    disabled: modelData.control !== "" && modelData.kind !== "info"
                              && !modelData.writable
                    // A chevron promises "this opens something". A choice we cannot write does
                    // not open anything, so it does not get one.
                    navigable: modelData.page !== "" || modelData.url !== ""
                               || (modelData.kind === "choice" && modelData.writable)
                    onTriggered: {
                        if (modelData.page !== "") settings.openPage(modelData.page);
                        else if (modelData.url !== "") Qt.openUrlExternally(modelData.url);
                        // A row backed by settingscontrols.py asks the system to change and then
                        // redraws from what the system answered — never from what was clicked.
                        else if (modelData.control !== "" && typeof settingsControls !== "undefined") {
                            if (modelData.kind === "option") {
                                settingsControls.set(modelData.control, modelData.option);
                                settings.goBack();
                            } else if (modelData.kind === "choice") {
                                settings.openPage("choice:" + modelData.control);
                            } else {
                                settingsControls.activate(modelData.control);
                            }
                            settings.reloadTree();
                        }
                        else if (modelData.pref !== "" && typeof prefs !== "undefined") {
                            prefs.toggle(modelData.pref);
                            settings.reloadTree();
                        }
                    }
                    }
                }
            }

            // Windows ends its pages with a help link; ours points at the project's issue tracker,
            // which is the only place help for this system actually exists.
            Row {
                spacing: 10
                Item { width: 1; height: 1 }
                SysIcon {
                    glyph: "info"; width: 16; height: 16
                    color: Theme.accent
                    anchors.verticalCenter: parent.verticalCenter
                }
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Получить помощь"
                    color: Theme.accent
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontCaption + 1
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: Qt.openUrlExternally(settings.tree ? settings.tree.helpUrl : "")
                    }
                }
            }
        }
    }

}
