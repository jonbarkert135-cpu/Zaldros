import QtQuick
import QtQuick.Controls
import ZaldrosTheme

// Zaldros Start. Windows 11 geometry: 640 x 726, 32 px padding, search field at the top, a 6-column
// pinned grid with 32 px icons, a Recommended list, and a footer with the user and power.
// "Все приложения" flips the body to the real installed-application list read from .desktop files.
Item {
    id: start
    objectName: "startPanel"
    property bool shown: false
    property var state: null
    property var system: null
    property var apps: null
    property var installed: null
    property var recent: null
    property int selectedIndex: -1
    signal appLaunched(int row)
    signal powerRequested()

    width: Theme.startWidth
    height: Theme.startHeight
    visible: opacity > 0.01
    opacity: shown ? 1 : 0
    y: shown ? baseY : baseY + 24
    property real baseY: 0
    enabled: shown

    Behavior on opacity { NumberAnimation { duration: Theme.animNormal; easing.type: Easing.OutCubic } }
    Behavior on y { NumberAnimation { duration: Theme.animSlow; easing.type: Easing.OutCubic } }

    // Settings > Персонализация > Пуск writes these; a switch that changes nothing is worse than
    // no switch at all (see zaldros_shell/prefs.py).
    property var prefValues: (typeof prefs !== "undefined" && prefs && prefs.values) ? prefs.values : ({})
    function shown_(key) { return prefValues[key] !== false }

    property bool allApps: false
    // The memory line below is the only live meter in this panel: tell the backend to sample
    // while it is on screen and to stop when it is not. Nothing here changes what is drawn.
    onShownChanged: {
        if (!shown) { allApps = false; selectedIndex = -1 }
        if (start.state && start.state.setMetersActive) start.state.setMetersActive(shown)
    }

    // Keyboard navigation (brief §5): arrows move the selection across the 6-column grid,
    // Enter launches, Escape closes. Focus follows the panel when Start opens.
    focus: shown
    Keys.onPressed: function(event) {
        var count = start.apps ? start.apps.rowCount() : 0;
        if (count === 0) return;
        if (event.key === Qt.Key_Right) { start.selectedIndex = Math.min(count - 1, start.selectedIndex + 1); event.accepted = true; }
        else if (event.key === Qt.Key_Left) { start.selectedIndex = Math.max(0, start.selectedIndex - 1); event.accepted = true; }
        else if (event.key === Qt.Key_Down) { start.selectedIndex = Math.min(count - 1, start.selectedIndex + 6); event.accepted = true; }
        else if (event.key === Qt.Key_Up) { start.selectedIndex = Math.max(0, start.selectedIndex - 6); event.accepted = true; }
        else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
            if (start.selectedIndex >= 0) start.appLaunched(start.selectedIndex);
            event.accepted = true;
        }
    }

    Rectangle {
        anchors.fill: parent
        radius: Theme.radiusMedium
        color: Theme.background
    }

    Rectangle {
        id: panel
        anchors.fill: parent
        radius: Theme.radiusMedium
        color: Theme.surfaceAcrylic
        border.width: 1
        border.color: Theme.borderStrong
        clip: true

        // --- search ------------------------------------------------------------------------
        Rectangle {
            id: search
            objectName: "startSearch"
            x: Theme.startPadding
            y: Theme.startPadding
            width: parent.width - Theme.startPadding * 2
            height: Theme.startSearchHeight
            radius: 6
            color: Theme.surface
            border.width: 1
            border.color: searchInput.activeFocus ? Theme.accent : Theme.border
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
                    id: searchInput
                    width: parent.width - 50
                    anchors.verticalCenter: parent.verticalCenter
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBody
                    clip: true
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        visible: searchInput.text.length === 0
                        text: "Поиск приложений, параметров и документов"
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBody
                    }
                }
            }
        }

        // --- section header ------------------------------------------------------------------
        Item {
            id: pinnedHeader
            x: Theme.startPadding
            width: parent.width - Theme.startPadding * 2
            anchors.top: search.bottom
            anchors.topMargin: 24
            height: 28
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: start.allApps ? "Все приложения" : "Закреплено"
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBody
                font.weight: Font.DemiBold
            }
            PillButton {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                label: start.allApps ? "Назад" : "Все приложения"
                trailingGlyph: start.allApps ? "" : "chevron-right"
                onTriggered: start.allApps = !start.allApps
            }
        }

        // --- pinned grid ---------------------------------------------------------------------
        GridView {
            id: pinnedGrid
            objectName: "startPinnedGrid"
            visible: !start.allApps
            x: Theme.startPadding
            anchors.top: pinnedHeader.bottom
            anchors.topMargin: 8
            width: parent.width - Theme.startPadding * 2
            height: Theme.startCellHeight * 3
            cellWidth: Math.floor(width / Theme.startColumns)
            cellHeight: Theme.startCellHeight
            interactive: false
            model: start.apps
            delegate: Item {
                width: pinnedGrid.cellWidth
                height: pinnedGrid.cellHeight
                Rectangle {
                    anchors.fill: parent
                    anchors.margins: 2
                    radius: Theme.radiusSmall + 1
                    color: pinArea.pressed ? Theme.pressed
                          : (start.selectedIndex === index ? Theme.selected
                          : (pinArea.containsMouse ? Theme.hover : "transparent"))
                    Behavior on color { ColorAnimation { duration: Theme.animFast } }
                }
                AppTile {
                    y: 12
                    width: Theme.startPinIcon
                    height: Theme.startPinIcon
                    baseColor: model.color
                    iconName: model.icon
                    label: model.name.substring(0, 1).toUpperCase()
                    dim: !model.installed
                    anchors.horizontalCenter: parent.horizontalCenter
                }
                Text {
                    y: 12 + Theme.startPinIcon + 6
                    width: pinnedGrid.cellWidth - 10
                    anchors.horizontalCenter: parent.horizontalCenter
                    horizontalAlignment: Text.AlignHCenter
                    text: model.name
                    color: model.installed ? Theme.textPrimary : Theme.textDisabled
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontCaption
                    elide: Text.ElideRight
                    maximumLineCount: 2
                    wrapMode: Text.WordWrap
                }
                MouseArea {
                    id: pinArea
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: { start.selectedIndex = index; start.appLaunched(index) }
                }
            }
        }

        // --- recommended ---------------------------------------------------------------------
        Item {
            id: recommendedHeader
            visible: !start.allApps && start.shown_("start.recent")
            x: Theme.startPadding
            width: parent.width - Theme.startPadding * 2
            anchors.top: pinnedGrid.bottom
            anchors.topMargin: 16
            height: 24
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: "Рекомендуем"
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBody
                font.weight: Font.DemiBold
            }
        }

        // Real recently modified files from the home directory (RecentModel). When nothing was
        // found the section says so — it is never filled with sample documents.
        Grid {
            id: recommended
            visible: !start.allApps && start.shown_("start.recent")
            x: Theme.startPadding
            anchors.top: recommendedHeader.bottom
            anchors.topMargin: 8
            width: parent.width - Theme.startPadding * 2
            columns: 2
            Repeater {
                model: start.recent
                delegate: Item {
                    width: recommended.width / 2
                    height: 48
                    Rectangle {
                        anchors.fill: parent
                        anchors.margins: 2
                        radius: Theme.radiusSmall
                        color: recentArea.pressed ? Theme.pressed
                               : (recentArea.containsMouse ? Theme.hover : "transparent")
                    }
                    Row {
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.left: parent.left
                        anchors.leftMargin: 10
                        spacing: 12
                        SysIcon {
                            glyph: model.glyph
                            width: 20; height: 20
                            color: Theme.textSecondary
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Column {
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 2
                            Text {
                                width: recommended.width / 2 - 60
                                elide: Text.ElideRight
                                text: model.name
                                color: Theme.textPrimary
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontCaption + 1
                            }
                            Text {
                                text: model.subtitle
                                color: Theme.textSecondary
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontCaption - 1
                            }
                        }
                    }
                    MouseArea { id: recentArea; anchors.fill: parent; hoverEnabled: true }
                }
            }
        }

        Text {
            visible: !start.allApps && start.shown_("start.recent")
                     && (!start.recent || start.recent.count === 0)
            x: Theme.startPadding
            anchors.top: recommendedHeader.bottom
            anchors.topMargin: 16
            width: parent.width - Theme.startPadding * 2
            wrapMode: Text.WordWrap
            text: "Недавних файлов не найдено — здесь появятся документы, с которыми вы работали."
            color: Theme.textSecondary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontCaption
        }

        // --- all applications list -------------------------------------------------------------
        ListView {
            id: allList
            visible: start.allApps
            x: Theme.startPadding
            anchors.top: pinnedHeader.bottom
            anchors.topMargin: 8
            width: parent.width - Theme.startPadding * 2
            height: Theme.startCellHeight * 3 + 152
            clip: true
            model: start.installed
            ScrollBar.vertical: ScrollBar { }
            delegate: Item {
                width: allList.width
                height: 44
                Rectangle {
                    anchors.fill: parent
                    anchors.rightMargin: 8
                    radius: Theme.radiusSmall
                    color: rowArea.pressed ? Theme.pressed
                          : (rowArea.containsMouse ? Theme.hover : "transparent")
                }
                Row {
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.left: parent.left
                    anchors.leftMargin: 10
                    spacing: 12
                    AppTile {
                        width: 24; height: 24
                        baseColor: model.color
                        iconName: model.icon
                        label: model.name.substring(0, 1).toUpperCase()
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    Column {
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 1
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
                    onClicked: start.installed.launchRow(index)
                }
            }
        }

        // --- footer ---------------------------------------------------------------------------
        Rectangle {
            id: footer
            objectName: "startFooter"
            anchors.bottom: parent.bottom
            width: parent.width
            height: Theme.startFooterHeight
            color: Theme.hover
            Rectangle { width: parent.width; height: 1; color: Theme.border }

            Row {
                anchors.left: parent.left
                anchors.leftMargin: Theme.startPadding
                anchors.verticalCenter: parent.verticalCenter
                spacing: 12
                Rectangle {
                    width: 32; height: 32; radius: 16
                    color: Theme.accent
                    anchors.verticalCenter: parent.verticalCenter
                    SysIcon {
                        anchors.centerIn: parent
                        glyph: "user"; width: 18; height: 18
                        color: Theme.accentText
                    }
                }
                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 1
                    Text {
                        text: start.system && start.system.userName ? start.system.userName : "пользователь"
                        color: Theme.textPrimary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBody
                    }
                    Text {
                        text: start.state && start.state.memoryPercent >= 0
                              ? ("Память: " + start.state.memoryPercent + " %")
                              : "Память: —"
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontCaption
                    }
                }
            }

            TrayButton {
                anchors.right: parent.right
                anchors.rightMargin: Theme.startPadding - 8
                anchors.verticalCenter: parent.verticalCenter
                height: 40
                glyph: "power"
                tooltip: "Завершение работы"
                onTriggered: start.powerRequested()
            }
        }
    }
}
