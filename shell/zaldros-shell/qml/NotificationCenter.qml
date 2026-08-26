import QtQuick
import ZaldrosTheme

// Notification centre and calendar, opened from the clock — the Windows 11 arrangement measured in
// assets/refs/win11_notification_center.png: a 360 px column holding the notification card above
// the month calendar, 12 px from the screen edge and from the taskbar.
//
// The calendar is real: it renders the current month and marks today. The notification list is
// empty until a notification service exists, and says exactly that.
Item {
    id: centre
    objectName: "notificationCentre"

    property bool shown: false
    property real baseY: 0

    width: Theme.notificationWidth
    height: column.implicitHeight
    visible: opacity > 0.01
    opacity: shown ? 1 : 0
    y: shown ? baseY : baseY + 16
    enabled: shown
    Behavior on opacity { NumberAnimation { duration: Theme.animNormal; easing.type: Easing.OutCubic } }
    Behavior on y { NumberAnimation { duration: Theme.animNormal; easing.type: Easing.OutCubic } }

    readonly property var today: new Date()
    readonly property var monthNames: ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль",
                                       "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
    readonly property var weekdayNames: ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

    // Monday-first grid of 42 cells: [{ day, current }]
    readonly property var days: {
        var year = today.getFullYear(), month = today.getMonth();
        var first = new Date(year, month, 1);
        var offset = (first.getDay() + 6) % 7;               // Monday = 0
        var daysInMonth = new Date(year, month + 1, 0).getDate();
        var daysBefore = new Date(year, month, 0).getDate();
        var cells = [];
        for (var i = 0; i < 42; i++) {
            var number = i - offset + 1;
            if (number < 1) cells.push({ day: daysBefore + number, current: false });
            else if (number > daysInMonth) cells.push({ day: number - daysInMonth, current: false });
            else cells.push({ day: number, current: true });
        }
        return cells;
    }

    Column {
        id: column
        width: parent.width
        spacing: 8

        // --- notifications --------------------------------------------------------------------
        Item {
            width: parent.width
            height: notificationBody.implicitHeight + 32

            Rectangle { anchors.fill: parent; radius: Theme.radiusMedium; color: Theme.background }
            Rectangle {
                anchors.fill: parent
                radius: Theme.radiusMedium
                color: Theme.surfaceAcrylic
                border.width: 1
                border.color: Theme.borderStrong
            }

            Column {
                id: notificationBody
                anchors.fill: parent
                anchors.margins: 16
                spacing: 10

                Item {
                    width: parent.width
                    height: 24
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "Уведомления"
                        color: Theme.textPrimary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBody
                        font.weight: Font.DemiBold
                    }
                    PillButton {
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        label: "Удалить все"
                    }
                }

                Text {
                    width: parent.width
                    wrapMode: Text.WordWrap
                    text: "Новых уведомлений нет. Служба уведомлений ещё не подключена к сеансу, "
                          + "поэтому здесь ничего не накапливается."
                    color: Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontCaption
                }
            }
        }

        // --- calendar --------------------------------------------------------------------------
        Item {
            width: parent.width
            height: calendarBody.implicitHeight + 32

            Rectangle { anchors.fill: parent; radius: Theme.radiusMedium; color: Theme.background }
            Rectangle {
                anchors.fill: parent
                radius: Theme.radiusMedium
                color: Theme.surfaceAcrylic
                border.width: 1
                border.color: Theme.borderStrong
            }

            Column {
                id: calendarBody
                anchors.fill: parent
                anchors.margins: 16
                spacing: 10

                Text {
                    text: centre.monthNames[centre.today.getMonth()] + " " + centre.today.getFullYear()
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBody
                    font.weight: Font.DemiBold
                }

                Row {
                    spacing: 0
                    Repeater {
                        model: centre.weekdayNames
                        delegate: Text {
                            width: (centre.width - 32) / 7
                            horizontalAlignment: Text.AlignHCenter
                            text: modelData
                            color: Theme.textSecondary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontCaption - 1
                        }
                    }
                }

                Grid {
                    columns: 7
                    Repeater {
                        model: centre.days
                        delegate: Item {
                            width: (centre.width - 32) / 7
                            height: 34
                            property bool isToday: modelData.current
                                                   && modelData.day === centre.today.getDate()
                            Rectangle {
                                anchors.centerIn: parent
                                width: 28; height: 28; radius: 14
                                color: parent.isToday ? Theme.accent
                                       : (dayArea.containsMouse ? Theme.hover : "transparent")
                            }
                            Text {
                                anchors.centerIn: parent
                                text: modelData.day
                                color: parent.isToday ? Theme.accentText
                                       : (modelData.current ? Theme.textPrimary : Theme.textDisabled)
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontCaption
                            }
                            MouseArea { id: dayArea; anchors.fill: parent; hoverEnabled: true }
                        }
                    }
                }
            }
        }
    }
}
