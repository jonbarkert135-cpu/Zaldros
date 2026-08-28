import QtQuick
import QtQuick.Controls
import ZaldrosTheme
import ".."

// Zaldros «Диспетчер задач», laid out like the Windows 11 22H2+ Task Manager: a left navigation
// rail with the pages (Процессы, Производительность, Автозагрузка), a Mica command bar with the
// search box and «Снять задачу», and a dense 32 px row list under a sortable header.
//
// Geometry reuses the already-measured Windows 11 tokens (system/theme/win11-reference.json →
// task_manager): 48 px command bar, 190 px rail, 32 px rows — the same values Explorer and
// Settings were measured to. There is no authentic Task Manager capture in the reference library
// yet, and that gap is recorded rather than papered over with invented numbers.
//
// Every row is a real process from /proc through ProcessModel. Columns whose value is not
// measurable show «—»: the first sample cannot know a CPU share, and a dash is the truth.
Item {
    id: taskManager
    property var model: null
    property var startup: null
    property int page: 0                       // 0 процессы, 1 производительность, 2 автозагрузка
    property string status: ""

    readonly property var summary: model ? model.summary : ({})
    readonly property var pages: [
        { id: "processes", title: "Процессы", glyph: "apps" },
        { id: "performance", title: "Производительность", glyph: "chart" },
        { id: "startup", title: "Автозагрузка", glyph: "power" }
    ]

    function endSelected(force) {
        if (!taskManager.model || processList.currentIndex < 0)
            return;
        var pid = processList.currentItem ? processList.currentItem.pid : -1;
        if (pid <= 0)
            return;
        var result = taskManager.model.endTask(pid, force === true);
        taskManager.status = result.ok
                ? "Процесс " + pid + ": отправлен " + (force === true ? "SIGKILL" : "SIGTERM")
                : "Процесс " + pid + ": " + result.detail;
    }

    Rectangle { anchors.fill: parent; color: Theme.appBackground }

    // --- navigation rail ---------------------------------------------------------------------
    Item {
        id: rail
        objectName: "taskManagerRail"
        width: Theme.sidebarWidth
        height: parent.height

        Column {
            y: 8
            width: parent.width
            spacing: 2
            Repeater {
                model: taskManager.pages
                delegate: Rectangle {
                    width: rail.width - 8
                    x: 4
                    height: 36
                    radius: Theme.radiusSmall
                    color: index === taskManager.page ? Theme.surfaceElevated
                         : railHover.containsMouse ? Theme.surfaceCard : "transparent"
                    Rectangle {                      // Windows 11 selection pill
                        visible: index === taskManager.page
                        width: 3; height: 16; radius: 1.5
                        x: 0
                        anchors.verticalCenter: parent.verticalCenter
                        color: Theme.accent
                    }
                    Text {
                        x: 16
                        anchors.verticalCenter: parent.verticalCenter
                        text: modelData.title
                        color: Theme.textPrimary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBody
                    }
                    MouseArea {
                        id: railHover
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: taskManager.page = index
                    }
                }
            }
        }
    }

    // --- command bar -------------------------------------------------------------------------
    Item {
        id: commandBar
        anchors.left: rail.right
        anchors.right: parent.right
        height: Theme.commandBarHeight

        Text {
            x: 16
            anchors.verticalCenter: parent.verticalCenter
            text: taskManager.pages[taskManager.page].title
            color: Theme.textPrimary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontSubtitle
        }

        Row {
            anchors.right: parent.right
            anchors.rightMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            spacing: 8

            Rectangle {
                width: 220; height: 32; radius: Theme.radiusSmall
                color: Theme.surface
                border.width: 1
                border.color: Theme.border
                visible: taskManager.page === 0
                TextInput {
                    id: searchField
                    anchors.fill: parent
                    anchors.leftMargin: 10
                    anchors.rightMargin: 10
                    verticalAlignment: TextInput.AlignVCenter
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontCaption
                    clip: true
                    onTextChanged: if (taskManager.model) taskManager.model.search(text)
                }
                Text {
                    x: 10
                    anchors.verticalCenter: parent.verticalCenter
                    visible: searchField.text === ""
                    text: "Имя или ИД процесса"
                    color: Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontCaption
                }
            }

            Rectangle {
                width: 116; height: 32; radius: Theme.radiusSmall
                visible: taskManager.page === 0
                color: endArea.containsMouse ? Theme.surfaceElevated : Theme.surface
                border.width: 1
                border.color: Theme.border
                Text {
                    anchors.centerIn: parent
                    text: "Снять задачу"
                    color: processList.currentIndex >= 0 ? Theme.textPrimary : Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontCaption
                }
                MouseArea {
                    id: endArea
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: taskManager.endSelected(false)
                }
            }
        }
    }

    // --- processes ----------------------------------------------------------------------------
    Item {
        anchors.left: rail.right
        anchors.right: parent.right
        anchors.top: commandBar.bottom
        anchors.bottom: parent.bottom
        visible: taskManager.page === 0

        Row {
            id: header
            height: 28
            width: parent.width
            Repeater {
                model: taskManager.model ? taskManager.model.columns : []
                delegate: Item {
                    width: index === 0 ? header.width - 560 : 80
                    height: header.height
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        x: 8
                        text: modelData.title
                            + (taskManager.model && taskManager.model.sortKey === modelData.key
                               ? (taskManager.model.sortDescending ? " ▾" : " ▴") : "")
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontCaption
                    }
                    MouseArea {
                        anchors.fill: parent
                        onClicked: if (taskManager.model) taskManager.model.sortBy(modelData.key)
                    }
                }
            }
        }

        ListView {
            id: processList
            objectName: "processList"
            anchors.top: header.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 28          // room for the status strip below
            clip: true
            model: taskManager.model
            currentIndex: -1
            delegate: Rectangle {
                id: processRow
                property int pid: model.pid
                // Captured here because the inner Repeater's delegate scope shadows `model`.
                property var cells: [model.cpuText, model.memText, model.diskText,
                                     model.threads, model.pid, model.user, model.stateText]
                width: processList.width
                height: Theme.listRowHeight
                color: ListView.isCurrentItem ? Theme.surfaceElevated
                     : rowHover.containsMouse ? Theme.surfaceCard : "transparent"
                Row {
                    anchors.fill: parent
                    Item {
                        width: processList.width - 560; height: parent.height
                        Text {
                            x: 8
                            anchors.verticalCenter: parent.verticalCenter
                            width: parent.width - 16
                            elide: Text.ElideRight
                            text: model.name
                            color: Theme.textPrimary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontCaption
                        }
                    }
                    Repeater {
                        model: processRow.cells
                        delegate: Item {
                            width: 80; height: Theme.listRowHeight
                            Text {
                                x: 8
                                anchors.verticalCenter: parent.verticalCenter
                                width: 64
                                elide: Text.ElideRight
                                text: modelData === undefined || modelData === null ? "—" : modelData
                                color: Theme.textSecondary
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontCaption
                            }
                        }
                    }
                }
                MouseArea {
                    id: rowHover
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: processList.currentIndex = index
                }
            }
        }
    }

    // --- performance --------------------------------------------------------------------------
    Item {
        anchors.left: rail.right
        anchors.right: parent.right
        anchors.top: commandBar.bottom
        anchors.bottom: parent.bottom
        visible: taskManager.page === 1

        Column {
            x: 16; y: 8
            spacing: 12
            width: parent.width - 32

            Repeater {
                model: [
                    { title: "ЦП", value: taskManager.summary.cpu, sub: "" },
                    { title: "Память", value: taskManager.summary.memory,
                      sub: taskManager.summary.memoryDetail },
                    { title: "Диск (чтение / запись)", value: taskManager.summary.disk, sub: "" },
                    { title: "Сеть (приём / отдача)", value: taskManager.summary.network, sub: "" },
                    { title: "Время работы", value: taskManager.summary.uptime, sub: "" }
                ]
                delegate: Rectangle {
                    width: parent.width
                    height: 60
                    radius: Theme.radiusMedium
                    color: Theme.surfaceCard
                    border.width: 1
                    border.color: Theme.border
                    Column {
                        x: 16
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 2
                        Text {
                            text: modelData.title
                            color: Theme.textPrimary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontBody
                        }
                        Text {
                            text: (modelData.value === undefined ? "—" : modelData.value)
                                  + (modelData.sub ? "   " + modelData.sub : "")
                            color: Theme.textSecondary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontCaption
                        }
                    }
                }
            }
        }
    }

    // --- startup ------------------------------------------------------------------------------
    Item {
        anchors.left: rail.right
        anchors.right: parent.right
        anchors.top: commandBar.bottom
        anchors.bottom: parent.bottom
        visible: taskManager.page === 2

        ListView {
            objectName: "startupList"
            anchors.fill: parent
            anchors.margins: 8
            clip: true
            model: taskManager.startup
            delegate: Rectangle {
                width: parent ? parent.width : 0
                height: 48
                radius: Theme.radiusMedium
                color: Theme.surfaceCard
                Column {
                    x: 12
                    anchors.verticalCenter: parent.verticalCenter
                    Text {
                        text: model.name
                        color: Theme.textPrimary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBody
                    }
                    Text {
                        text: model.command
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontCaption
                    }
                }
                Text {
                    anchors.right: parent.right
                    anchors.rightMargin: 12
                    anchors.verticalCenter: parent.verticalCenter
                    text: model.enabled ? "Включено" : "Отключено"
                    color: model.enabled ? Theme.accent : Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontCaption
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        var result = taskManager.startup.toggle(index);
                        taskManager.status = result.ok ? "" : result.detail;
                    }
                }
            }
        }
    }

    // --- status strip --------------------------------------------------------------------------
    Rectangle {
        id: statusBar
        anchors.left: rail.right
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 28
        color: "transparent"
        Text {
            x: 12
            anchors.verticalCenter: parent.verticalCenter
            text: taskManager.status !== "" ? taskManager.status
                  : (taskManager.summary.processes === undefined ? "Измерение…"
                     : "Процессов: " + taskManager.summary.processes
                       + "    Потоков: " + taskManager.summary.threads
                       + "    ЦП: " + taskManager.summary.cpu)
            color: Theme.textSecondary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontCaption
        }
    }
}
