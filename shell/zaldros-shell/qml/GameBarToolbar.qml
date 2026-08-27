import QtQuick
import ZaldrosTheme

// Win+G — the floating game bar itself: the pill at the top of the screen that owns the widgets.
//
// Measured from the maintainer's capture (2026-08-26, 125 %): the pill is 654 × 67 px there, so
// 523 × 54 logical; its middle group has its own lighter background 279 px = 223 wide; the icon
// buttons sit on a 50 px = 40 pitch and the active widget button is a filled 40 px = 32 square.
// Recorded in system/theme/win11-reference.json → game_bar.bar and checked by parity.
//
// Three groups, exactly as Windows lays them out: what is running on the left, the widget buttons
// in the middle, the status and settings on the right. Every reading here is real — the clock and
// the battery come from the same SystemState the taskbar uses — and buttons for things Zaldros
// does not have (Xbox friends, Edge) are simply not drawn rather than drawn dead.
Item {
    id: bar
    objectName: "gameBarToolbar"

    property bool shown: false
    property var state: null
    property var system: null
    property var capture: null
    property bool captureActive: false
    property bool performanceActive: false
    signal captureToggled()
    signal performanceToggled()
    signal settingsRequested()

    width: Theme.gameBarBarWidth
    height: Theme.gameBarBarHeight
    visible: opacity > 0.01
    opacity: shown ? 1 : 0
    enabled: shown
    Behavior on opacity { NumberAnimation { duration: Theme.animNormal; easing.type: Easing.OutCubic } }

    Rectangle { anchors.fill: parent; radius: Theme.gameBarBarRadius; color: Theme.background }
    Rectangle {
        anchors.fill: parent
        radius: Theme.gameBarBarRadius
        color: Theme.surfaceAcrylic
        border.width: 1
        border.color: Theme.borderStrong
    }

    component BarButton: Rectangle {
        id: button
        property alias glyph: buttonIcon.glyph
        property string hint: ""
        property bool active: false
        signal triggered()

        width: Theme.gameBarBarButton
        height: Theme.gameBarBarButton
        radius: Theme.radiusSmall
        color: active ? Theme.textPrimary
               : (buttonArea.pressed ? Theme.pressed
                  : (buttonArea.containsMouse ? Theme.hover : "transparent"))
        Behavior on color { ColorAnimation { duration: Theme.animFast } }

        SysIcon {
            id: buttonIcon
            anchors.centerIn: parent
            width: Theme.gameBarBarGlyph
            height: Theme.gameBarBarGlyph
            // the active widget button in Windows is a light tile with a dark glyph
            color: button.active ? Theme.background : Theme.textPrimary
        }
        ToolTipLabel { text: button.hint; visible: buttonArea.containsMouse }
        MouseArea {
            id: buttonArea
            anchors.fill: parent
            hoverEnabled: true
            onClicked: button.triggered()
        }
    }

    Item {
        anchors.fill: parent
        anchors.leftMargin: Theme.gameBarBarPadding
        anchors.rightMargin: Theme.gameBarBarPadding

        // --- what is running -----------------------------------------------------------------
        Row {
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            spacing: 6

            Rectangle {
                objectName: "gameBarRunningTile"
                width: Theme.gameBarBarTile
                height: Theme.gameBarBarTile
                radius: Theme.radiusSmall
                color: Theme.surfaceCard
                border.width: 1
                border.color: Theme.border
                anchors.verticalCenter: parent.verticalCenter

                ZaldrosMark {
                    anchors.centerIn: parent
                    width: parent.width - 12
                    height: parent.height - 12
                }
            }
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: "›"
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBody
                color: Theme.textSecondary
            }
            BarButton {
                objectName: "gameBarWidgetMenu"
                glyph: "grid"
                hint: "Мини-приложения"
                anchors.verticalCenter: parent.verticalCenter
                onTriggered: bar.settingsRequested()
            }
        }

        // --- the widget buttons, on their own slightly lighter field --------------------------
        Item {
            anchors.horizontalCenter: parent.horizontalCenter
            // Windows sizes this field to the widget buttons it holds (five there, three here —
            // Xbox friends and Edge are not ours to draw), so the width follows the row.
            width: widgetRow.implicitWidth + 2 * Theme.gameBarBarGroupPadding
            height: parent.height

            Rectangle {
                anchors.centerIn: parent
                width: parent.width
                height: parent.height
                color: Theme.surfaceElevated
                opacity: 0.6
            }

            Row {
                id: widgetRow
                anchors.centerIn: parent
                spacing: Theme.gameBarBarGap

                BarButton {
                    objectName: "gameBarVolume"
                    glyph: bar.system && bar.system.volumePercent === 0 ? "volume" : "speaker"
                    hint: bar.system && bar.system.volumeAvailable
                          ? "Звук: " + bar.system.volumePercent + " %" : "Звук: нет данных"
                }
                BarButton {
                    objectName: "gameBarCaptureButton"
                    glyph: "camera"
                    hint: "Записать"
                    active: bar.captureActive
                    onTriggered: bar.captureToggled()
                }
                BarButton {
                    objectName: "gameBarPerformanceButton"
                    glyph: "screen"
                    hint: "Производительность"
                    active: bar.performanceActive
                    onTriggered: bar.performanceToggled()
                }
            }
        }

        // --- clock, battery, settings ----------------------------------------------------------
        Row {
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            spacing: Theme.gameBarBarGap

            Text {
                objectName: "gameBarClock"
                anchors.verticalCenter: parent.verticalCenter
                text: bar.state ? bar.state.timeText : ""
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSubtitle
                color: Theme.textPrimary
            }
            BarButton {
                objectName: "gameBarBattery"
                glyph: "battery"
                hint: bar.system && bar.system.batteryAvailable
                      ? "Батарея: " + bar.system.batteryPercent + " %"
                      : "Батарея: " + (bar.system ? bar.system.batteryDetail : "нет данных")
                anchors.verticalCenter: parent.verticalCenter
            }
            BarButton {
                objectName: "gameBarSettings"
                glyph: "settings"
                hint: "Параметры игровой панели"
                anchors.verticalCenter: parent.verticalCenter
                onTriggered: bar.settingsRequested()
            }
        }
    }
}
