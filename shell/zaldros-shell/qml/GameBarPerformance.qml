import QtQuick
import ZaldrosTheme

// Win+G → the «Производительность» widget.
//
// Same frame as the capture widget (306 logical wide, the measured game-bar widget width), and the
// same rule about content: every number here is read from /proc on this machine — CPU load from
// the difference between two /proc/stat samples, memory from /proc/meminfo. A reading that cannot
// be taken shows «—», never a plausible-looking number. Windows also graphs GPU and FPS here; we
// do not measure either yet, so neither is drawn.
Item {
    id: widget
    objectName: "gameBarPerformance"

    property bool shown: false
    property var state: null
    signal closeRequested()

    // Sample /proc only while the widget is open (see ShellState.setMetersActive). Behaviour
    // only — the layout, the colours and the strings are untouched.
    onShownChanged: if (widget.state && widget.state.setMetersActive) widget.state.setMetersActive(shown)

    width: Theme.gameBarWidth
    height: body.implicitHeight + 2 * Theme.gameBarPadding
    visible: opacity > 0.01
    opacity: shown ? 1 : 0
    enabled: shown
    Behavior on opacity { NumberAnimation { duration: Theme.animNormal; easing.type: Easing.OutCubic } }

    Rectangle { anchors.fill: parent; radius: Theme.radiusMedium; color: Theme.background }
    Rectangle {
        anchors.fill: parent
        radius: Theme.radiusMedium
        color: Theme.surfaceAcrylic
        border.width: 1
        border.color: Theme.borderStrong
    }

    Column {
        id: body
        anchors.fill: parent
        anchors.margins: Theme.gameBarPadding
        spacing: 12

        Item {
            width: parent.width
            height: Theme.gameBarHeader - Theme.gameBarPadding

            Row {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                spacing: 8
                SysIcon {
                    glyph: "screen"; width: 16; height: 16
                    anchors.verticalCenter: parent.verticalCenter
                    color: Theme.textPrimary
                }
                Text {
                    text: "Производительность"
                    anchors.verticalCenter: parent.verticalCenter
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSubtitle
                    color: Theme.textPrimary
                }
            }
            IconButton {
                glyph: "close"
                tooltip: "Закрыть"
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                onTriggered: widget.closeRequested()
            }
        }

        component Meter: Column {
            property string label: ""
            property int value: -1
            width: parent ? parent.width : 0
            spacing: 6

            Row {
                width: parent.width
                Text {
                    text: parent.parent.label
                    width: parent.width - readout.implicitWidth
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontCaption
                    color: Theme.textSecondary
                }
                Text {
                    id: readout
                    text: parent.parent.value < 0 ? "—" : parent.parent.value + " %"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontCaption
                    color: Theme.textPrimary
                }
            }
            Rectangle {
                width: parent.width
                height: 6
                radius: 3
                color: Theme.surface
                Rectangle {
                    width: parent.parent.value < 0 ? 0 : parent.width * parent.parent.value / 100
                    height: parent.height
                    radius: parent.radius
                    color: Theme.accent
                    Behavior on width { NumberAnimation { duration: Theme.animNormal } }
                }
            }
        }

        Meter { label: "ЦП"; value: widget.state ? widget.state.cpuPercent : -1 }
        Meter { label: "ОЗУ"; value: widget.state ? widget.state.memoryPercent : -1 }

        Text {
            width: parent.width
            text: "ГП и кадры в секунду здесь не показаны: Zaldros их пока не измеряет."
            wrapMode: Text.WordWrap
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontCaption
            color: Theme.textSecondary
        }
    }
}
