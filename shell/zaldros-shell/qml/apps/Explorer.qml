import QtQuick
import QtQuick.Controls
import ZaldrosTheme
import ".."

// Zaldros file manager, laid out to the measured Windows 11 Explorer
// (system/theme/win11-reference.json → explorer): 40 px tab strip, 48 px navigation bar,
// 48 px command bar, 190 px sidebar, 32 px rows, #191919 body in dark mode.
//
// It lists this machine's real files through FileModel: no sample rows, no placeholder copy.
Item {
    id: explorer
    property var model: null

    // Real operations on real files. The commands below call FileModel, which calls
    // zaldros_shell/files.py: create never overwrites, delete goes to the freedesktop bin.
    property int renamingRow: -1
    focus: true

    function newFolder() {
        var created = explorer.model ? explorer.model.createFolder() : "";
        if (created === "")
            return;
        var row = explorer.model.rowForPath(created);
        fileList.currentIndex = row;
        explorer.renamingRow = row;   // Windows drops straight into rename on a new folder
    }
    function renameSelected() {
        if (fileList.currentIndex >= 0)
            explorer.renamingRow = fileList.currentIndex;
    }
    function commitRename(row, name) {
        explorer.renamingRow = -1;
        if (explorer.model && name !== "")
            explorer.model.renameRow(row, name);
    }
    function deleteSelected() {
        if (explorer.model && fileList.currentIndex >= 0)
            explorer.model.deleteRow(fileList.currentIndex);
    }

    function openRowMenu(row, point) {
        rowMenu.row = row;
        rowMenu.x = Math.min(point.x, explorer.width - rowMenu.width - 8);
        rowMenu.y = Math.min(point.y, explorer.height - rowMenu.height - 8);
        rowMenu.shown = true;
    }

    Keys.onPressed: function (event) {
        if (event.key === Qt.Key_F2) { explorer.renameSelected(); event.accepted = true; }
        else if (event.key === Qt.Key_Delete) { explorer.deleteSelected(); event.accepted = true; }
        else if (event.key === Qt.Key_F5) { explorer.model.reload(); event.accepted = true; }
    }

    Rectangle {
        anchors.fill: parent
        color: Theme.appBackground
    }

    // --- navigation bar ------------------------------------------------------------------------
    Item {
        id: navBar
        objectName: "explorerNavBar"
        width: parent.width
        height: Theme.navBarHeight

        Row {
            id: navButtons
            anchors.verticalCenter: parent.verticalCenter
            anchors.left: parent.left
            anchors.leftMargin: 8
            spacing: 2
            IconButton {
                glyph: "arrow-left"; tooltip: "Назад"
                enabled: explorer.model ? explorer.model.canGoBack : false
                onTriggered: explorer.model.goBack()
            }
            IconButton {
                glyph: "arrow-right"; tooltip: "Вперёд"
                enabled: explorer.model ? explorer.model.canGoForward : false
                onTriggered: explorer.model.goForward()
            }
            IconButton {
                glyph: "arrow-up"; tooltip: "Вверх"
                onTriggered: explorer.model.goUp()
            }
            IconButton {
                glyph: "refresh"; tooltip: "Обновить"
                onTriggered: explorer.model.reload()
            }
        }

        // address bar with real breadcrumbs
        Rectangle {
            id: addressBar
            anchors.verticalCenter: parent.verticalCenter
            anchors.left: navButtons.right
            anchors.leftMargin: 8
            anchors.right: searchBox.left
            anchors.rightMargin: 8
            height: 32
            radius: Theme.radiusSmall
            color: Theme.dark ? "#1f1f1f" : "#ffffff"
            border.width: 1
            border.color: Theme.border
            clip: true

            Row {
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                anchors.leftMargin: 10
                spacing: 2
                SysIcon {
                    glyph: "home"; width: 14; height: 14
                    color: Theme.textSecondary
                    anchors.verticalCenter: parent.verticalCenter
                }
                Repeater {
                    model: explorer.model ? explorer.model.breadcrumbs : []
                    delegate: Row {
                        spacing: 2
                        SysIcon {
                            glyph: "chevron-right"; width: 10; height: 10
                            color: Theme.textDisabled
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Rectangle {
                            width: crumb.implicitWidth + 12
                            height: 24
                            radius: Theme.radiusSmall
                            color: crumbArea.containsMouse ? Theme.hover : "transparent"
                            anchors.verticalCenter: parent.verticalCenter
                            Text {
                                id: crumb
                                anchors.centerIn: parent
                                text: modelData.name
                                color: Theme.textPrimary
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontCaption
                            }
                            MouseArea {
                                id: crumbArea
                                anchors.fill: parent
                                hoverEnabled: true
                                onClicked: explorer.model.navigate(modelData.path)
                            }
                        }
                    }
                }
            }
        }

        Rectangle {
            id: searchBox
            anchors.verticalCenter: parent.verticalCenter
            anchors.right: parent.right
            anchors.rightMargin: 8
            width: 220
            height: 32
            radius: Theme.radiusSmall
            color: Theme.dark ? "#1f1f1f" : "#ffffff"
            border.width: 1
            border.color: Theme.border
            Row {
                anchors.fill: parent
                anchors.leftMargin: 10
                anchors.rightMargin: 10
                spacing: 8
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    width: parent.width - 30
                    elide: Text.ElideRight
                    text: "Поиск: " + (explorer.model ? explorer.model.breadcrumbs[explorer.model.breadcrumbs.length - 1].name : "")
                    color: Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontCaption
                }
                SysIcon {
                    anchors.verticalCenter: parent.verticalCenter
                    glyph: "search"; width: 14; height: 14
                    color: Theme.textSecondary
                }
            }
        }
    }

    // --- command bar ----------------------------------------------------------------------------
    Item {
        id: commandBar
        objectName: "explorerCommandBar"
        anchors.top: navBar.bottom
        width: parent.width
        height: Theme.commandBarHeight

        Row {
            anchors.verticalCenter: parent.verticalCenter
            anchors.left: parent.left
            anchors.leftMargin: 12
            spacing: 2

            CommandButton {
                objectName: "explorerNewButton"
                glyph: "add-circle"; label: "Создать"; trailing: "chevron-down"
                onTriggered: explorer.newFolder()
            }
            Rectangle { width: 1; height: 20; color: Theme.border; anchors.verticalCenter: parent.verticalCenter }
            IconButton { glyph: "cut"; tooltip: "Вырезать" }
            IconButton { glyph: "copy"; tooltip: "Копировать" }
            IconButton { glyph: "paste"; tooltip: "Вставить" }
            IconButton {
                objectName: "explorerRenameButton"
                glyph: "rename"; tooltip: "Переименовать"
                enabled: fileList.currentIndex >= 0
                onTriggered: explorer.renameSelected()
            }
            IconButton { glyph: "share"; tooltip: "Поделиться" }
            IconButton {
                objectName: "explorerDeleteButton"
                glyph: "delete"; tooltip: "Удалить"
                enabled: fileList.currentIndex >= 0
                onTriggered: explorer.deleteSelected()
            }
            Rectangle { width: 1; height: 20; color: Theme.border; anchors.verticalCenter: parent.verticalCenter }
            CommandButton { glyph: "sort"; label: "Сортировать"; trailing: "chevron-down" }
            CommandButton { glyph: "view"; label: "Просмотреть"; trailing: "chevron-down" }
            CommandButton { glyph: "filter"; label: "Фильтр"; trailing: "chevron-down" }
            IconButton { glyph: "more"; tooltip: "Дополнительно" }
        }
    }

    // --- sidebar -----------------------------------------------------------------------------------
    Rectangle {
        id: sidebar
        objectName: "explorerSidebar"
        anchors.top: commandBar.bottom
        anchors.bottom: statusBar.top
        width: Theme.sidebarWidth
        color: Theme.appBackground

        Column {
            anchors.fill: parent
            anchors.margins: 8
            spacing: 1

            Repeater {
                model: explorer.model ? explorer.model.shortcuts : []
                delegate: Rectangle {
                    width: sidebar.width - 16
                    height: 30
                    radius: Theme.radiusSmall
                    color: explorer.model && explorer.model.path === modelData.path
                           ? Theme.selected : (shortcutArea.containsMouse ? Theme.hover : "transparent")
                    Row {
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.left: parent.left
                        anchors.leftMargin: 8
                        spacing: 10
                        Image {
                            width: 16; height: 16
                            source: "image://zaldrosicon/app/" + modelData.icon
                            sourceSize.width: 32; sourceSize.height: 32
                            asynchronous: false
                            fillMode: Image.PreserveAspectFit
                            smooth: true
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: modelData.name
                            color: Theme.textPrimary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontCaption
                        }
                    }
                    SysIcon {
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.right: parent.right
                        anchors.rightMargin: 8
                        glyph: "pin"; width: 12; height: 12
                        color: Theme.textDisabled
                    }
                    MouseArea {
                        id: shortcutArea
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: explorer.model.navigate(modelData.path)
                    }
                }
            }
        }
    }

    Rectangle {
        anchors.top: commandBar.bottom
        anchors.bottom: statusBar.top
        anchors.left: sidebar.right
        width: 1
        color: Theme.border
    }

    // --- file list ----------------------------------------------------------------------------------
    Item {
        id: listArea
        anchors.top: commandBar.bottom
        anchors.left: sidebar.right
        anchors.right: parent.right
        anchors.bottom: statusBar.top
        anchors.leftMargin: 1

        // column header
        Item {
            id: header
            width: parent.width
            height: 30
            Row {
                anchors.fill: parent
                anchors.leftMargin: 16
                Text {
                    width: parent.width * 0.44
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Имя"; color: Theme.textSecondary
                    font.family: Theme.fontFamily; font.pixelSize: Theme.fontCaption
                }
                Text {
                    width: parent.width * 0.24
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Дата изменения"; color: Theme.textSecondary
                    font.family: Theme.fontFamily; font.pixelSize: Theme.fontCaption
                }
                Text {
                    width: parent.width * 0.20
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Тип"; color: Theme.textSecondary
                    font.family: Theme.fontFamily; font.pixelSize: Theme.fontCaption
                }
                Text {
                    width: parent.width * 0.12
                    anchors.verticalCenter: parent.verticalCenter
                    horizontalAlignment: Text.AlignRight
                    text: "Размер"; color: Theme.textSecondary
                    font.family: Theme.fontFamily; font.pixelSize: Theme.fontCaption
                }
            }
            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.border }
        }

        ListView {
            id: fileList
            objectName: "explorerFileList"
            anchors.top: header.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            clip: true
            model: explorer.model
            currentIndex: -1
            ScrollBar.vertical: ScrollBar { }
            delegate: Item {
                width: fileList.width
                height: Theme.listRowHeight
                Rectangle {
                    anchors.fill: parent
                    anchors.leftMargin: 4
                    anchors.rightMargin: 8
                    radius: Theme.radiusSmall
                    color: fileList.currentIndex === index ? Theme.selected
                           : (rowArea.containsMouse ? Theme.hover : "transparent")
                }
                Row {
                    anchors.fill: parent
                    anchors.leftMargin: 16
                    Row {
                        width: parent.width * 0.44
                        spacing: 10
                        anchors.verticalCenter: parent.verticalCenter
                        Image {
                            width: 16; height: 16
                            anchors.verticalCenter: parent.verticalCenter
                            source: model.isDir ? "image://zaldrosicon/app/folder" : ""
                            sourceSize.width: 32; sourceSize.height: 32
                            asynchronous: false
                            fillMode: Image.PreserveAspectFit
                            visible: model.isDir && status === Image.Ready
                        }
                        SysIcon {
                            visible: !model.isDir
                            anchors.verticalCenter: parent.verticalCenter
                            glyph: model.glyph
                            width: 16; height: 16
                            color: Theme.textSecondary
                        }
                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            width: parent.width - 32
                            elide: Text.ElideRight
                            text: model.name
                            visible: explorer.renamingRow !== index
                            color: Theme.textPrimary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontCaption
                        }
                        // Inline rename, the way Explorer does it: the row turns into a field with
                        // the name selected, Enter commits, Escape and focus loss cancel.
                        Rectangle {
                            objectName: explorer.renamingRow === index ? "explorerRenameField" : ""
                            visible: explorer.renamingRow === index
                            anchors.verticalCenter: parent.verticalCenter
                            width: parent.width - 32
                            height: 22
                            radius: Theme.radiusSmall
                            color: Theme.dark ? "#1f1f1f" : "#ffffff"
                            border.width: 1
                            border.color: Theme.accent
                            TextInput {
                                id: renameField
                                anchors.fill: parent
                                anchors.leftMargin: 6
                                anchors.rightMargin: 6
                                verticalAlignment: TextInput.AlignVCenter
                                text: model.name
                                color: Theme.textPrimary
                                selectionColor: Theme.accent
                                selectedTextColor: "#ffffff"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontCaption
                                onVisibleChanged: if (visible) { text = model.name; forceActiveFocus(); selectAll(); }
                                onAccepted: explorer.commitRename(index, text)
                                Keys.onEscapePressed: explorer.renamingRow = -1
                            }
                        }
                    }
                    Text {
                        width: parent.width * 0.24
                        anchors.verticalCenter: parent.verticalCenter
                        text: model.modified
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily; font.pixelSize: Theme.fontCaption
                    }
                    Text {
                        width: parent.width * 0.20
                        anchors.verticalCenter: parent.verticalCenter
                        text: model.kind
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily; font.pixelSize: Theme.fontCaption
                    }
                    Text {
                        width: parent.width * 0.12
                        anchors.verticalCenter: parent.verticalCenter
                        horizontalAlignment: Text.AlignRight
                        text: model.size
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily; font.pixelSize: Theme.fontCaption
                    }
                }
                MouseArea {
                    id: rowArea
                    anchors.fill: parent
                    hoverEnabled: true
                    acceptedButtons: Qt.LeftButton | Qt.RightButton
                    onClicked: function (mouse) {
                        fileList.currentIndex = index;
                        if (mouse.button === Qt.RightButton)
                            explorer.openRowMenu(index, mapToItem(explorer, mouse.x, mouse.y));
                    }
                    onDoubleClicked: explorer.model.openRow(index)
                }
            }
        }

        // honest empty / error states
        Text {
            anchors.centerIn: parent
            visible: explorer.model && explorer.model.count === 0
            width: parent.width - 80
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            text: explorer.model && explorer.model.errorText !== ""
                  ? explorer.model.errorText : "Эта папка пуста"
            color: Theme.textSecondary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontCaption + 1
        }
    }

    // --- status bar ------------------------------------------------------------------------------------
    Item {
        id: statusBar
        anchors.bottom: parent.bottom
        width: parent.width
        height: 26
        Rectangle { width: parent.width; height: 1; color: Theme.border }
        Text {
            anchors.verticalCenter: parent.verticalCenter
            anchors.left: parent.left
            anchors.leftMargin: 12
            text: explorer.model ? ("Элементов: " + explorer.model.count) : ""
            color: Theme.textSecondary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontCaption - 1
        }
    }

    // --- context menu on a row -------------------------------------------------------------
    // The same Windows 11 menu component the desktop uses; only the entries that really work are
    // listed, because a menu item that does nothing is worse than no menu item.
    ContextMenu {
        id: rowMenu
        objectName: "explorerRowMenu"
        z: 50
        property int row: -1
        minWidth: 240
        items: [
            { label: "Открыть", glyph: "folder", action: "open" },
            { separator: true },
            { label: "Переименовать", glyph: "rename", shortcut: "F2", action: "rename" },
            { label: "Удалить", glyph: "delete", shortcut: "Del", action: "delete" },
            { separator: true },
            { label: "Создать папку", glyph: "add-circle", action: "new-folder" },
            { label: "Обновить", glyph: "refresh", shortcut: "F5", action: "refresh" }
        ]
        onItemChosen: function (action) {
            rowMenu.shown = false;
            if (action === "open") explorer.model.openRow(rowMenu.row);
            else if (action === "rename") { fileList.currentIndex = rowMenu.row; explorer.renameSelected(); }
            else if (action === "delete") { fileList.currentIndex = rowMenu.row; explorer.deleteSelected(); }
            else if (action === "new-folder") explorer.newFolder();
            else if (action === "refresh") explorer.model.reload();
        }
    }
    MouseArea {
        anchors.fill: parent
        z: 49
        visible: rowMenu.shown
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        onClicked: rowMenu.shown = false
    }
}
