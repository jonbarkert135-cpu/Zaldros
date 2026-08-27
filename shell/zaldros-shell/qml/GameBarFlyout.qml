import QtQuick
import ZaldrosTheme

// Win+G — the capture widget of the game bar.
//
// Geometry measured from the maintainer's own Windows 11 capture (2026-08-26, 125 % scale):
// the «Записать» widget is 383 px wide and 274 px tall in that shot, its four tiles are 70 px
// squares on a 90 px pitch, and the panel edge sits 21 px from the first tile. Divided by 1.25:
// 306 × 219, tiles 56 on a 72 pitch, padding 17. Recorded in system/theme/win11-reference.json →
// game_bar and re-checked by tools/visual/parity.py.
//
// Every tile here is wired to zaldros_shell/capture.py through model.GameBarModel, and a tile
// whose tool is not installed is disabled with the reason printed under the row — Windows shows
// the same four tiles on every machine and lets you press ones that quietly do nothing.
Item {
    id: flyout
    objectName: "gameBarFlyout"

    property bool shown: false
    property bool pinned: true
    property var capture: null
    signal closeRequested()

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

        // --- header ------------------------------------------------------------------------
        Item {
            width: parent.width
            height: Theme.gameBarHeader - Theme.gameBarPadding

            Row {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                spacing: 8
                SysIcon {
                    glyph: "camera"; width: 16; height: 16
                    anchors.verticalCenter: parent.verticalCenter
                    color: Theme.textPrimary
                }
                Text {
                    text: "Записать"
                    anchors.verticalCenter: parent.verticalCenter
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSubtitle
                    color: Theme.textPrimary
                }
            }
            Row {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                spacing: 2
                IconButton {
                    glyph: "pin"
                    tooltip: flyout.pinned ? "Открепить" : "Закрепить"
                    opacity: flyout.pinned ? 1.0 : 0.55
                    onTriggered: flyout.pinned = !flyout.pinned
                }
                IconButton {
                    glyph: "close"
                    tooltip: "Закрыть"
                    onTriggered: flyout.closeRequested()
                }
            }
        }

        // --- the four tiles ------------------------------------------------------------------
        Row {
            id: tiles
            spacing: Theme.gameBarTileGap

            component Tile: Rectangle {
                id: tile
                property alias glyph: tileIcon.glyph
                property string hint: ""
                property bool active: false
                property bool available: true
                signal triggered()

                width: Theme.gameBarTile
                height: Theme.gameBarTile
                radius: Theme.radiusSmall
                // Windows draws these as flat filled squares with no outline; the outline was the
                // loudest thing wrong with the first cut of this widget.
                color: active ? Theme.accent
                       : (tileArea.pressed ? Theme.pressed
                          : (tileArea.containsMouse ? Theme.surfaceElevated : Theme.surfaceCard))
                border.width: 0
                opacity: available ? 1.0 : 0.4
                Behavior on color { ColorAnimation { duration: Theme.animFast } }

                SysIcon {
                    id: tileIcon
                    anchors.centerIn: parent
                    width: 20; height: 20
                    color: Theme.textPrimary
                }
                ToolTipLabel { text: tile.hint; visible: tileArea.containsMouse }
                MouseArea {
                    id: tileArea
                    anchors.fill: parent
                    hoverEnabled: true
                    enabled: tile.available
                    onClicked: tile.triggered()
                }
            }

            Tile {
                objectName: "gameBarScreenshot"
                glyph: "image"
                hint: "Сделать снимок экрана"
                available: flyout.capture ? flyout.capture.canScreenshot : false
                onTriggered: flyout.capture.takeScreenshot()
            }
            Tile {
                objectName: "gameBarLastSeconds"
                glyph: "history"
                // Windows records the last 30 seconds from a ring buffer the compositor does not
                // give us; an unavailable tile says so rather than pretending.
                hint: "Записать последние 30 секунд — нужен буфер записи, его пока нет"
                available: false
            }
            Tile {
                objectName: "gameBarRecord"
                glyph: "record"
                hint: flyout.capture && flyout.capture.recording ? "Остановить запись" : "Начать запись"
                active: flyout.capture ? flyout.capture.recording : false
                available: flyout.capture ? flyout.capture.canRecord : false
                onTriggered: flyout.capture.toggleRecording()
            }
            Tile {
                objectName: "gameBarMic"
                glyph: "microphone"
                hint: flyout.capture && flyout.capture.micEnabled
                      ? "Микрофон включён" : "Микрофон выключен"
                active: flyout.capture ? flyout.capture.micEnabled : false
                available: flyout.capture ? flyout.capture.canRecord : false
                onTriggered: flyout.capture.toggleMic()
            }
        }

        // --- recording state and the last result ---------------------------------------------
        Row {
            width: parent.width
            spacing: 8
            visible: flyout.capture ? flyout.capture.recording : false

            Rectangle {
                width: 10; height: 10; radius: 5
                anchors.verticalCenter: parent.verticalCenter
                color: Theme.danger !== undefined ? Theme.danger : "#e81123"
                SequentialAnimation on opacity {
                    running: flyout.capture ? flyout.capture.recording : false
                    loops: Animation.Infinite
                    NumberAnimation { to: 0.25; duration: 700 }
                    NumberAnimation { to: 1.0; duration: 700 }
                }
            }
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: flyout.capture ? flyout.capture.elapsedText : "0:00"
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontCaption
                color: Theme.textPrimary
            }
        }

        Text {
            objectName: "gameBarStatus"
            width: parent.width
            visible: text.length > 0
            text: flyout.capture ? flyout.capture.status : ""
            wrapMode: Text.WordWrap
            maximumLineCount: 3
            elide: Text.ElideRight
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontCaption
            color: Theme.textSecondary
        }

        // --- footer ---------------------------------------------------------------------------
        Rectangle { width: parent.width; height: 1; color: Theme.border }

        Rectangle {
            id: openFolder
            width: parent.width
            height: Theme.gameBarFooter - Theme.gameBarPadding
            radius: Theme.radiusSmall
            color: folderArea.pressed ? Theme.pressed
                   : (folderArea.containsMouse ? Theme.hover : "transparent")
            Behavior on color { ColorAnimation { duration: Theme.animFast } }

            Row {
                anchors.left: parent.left
                anchors.leftMargin: 8
                anchors.verticalCenter: parent.verticalCenter
                spacing: 10
                SysIcon {
                    glyph: "folder"; width: 16; height: 16
                    anchors.verticalCenter: parent.verticalCenter
                    color: Theme.textPrimary
                }
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Просмотреть мои записи"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBody
                    color: Theme.textPrimary
                }
            }
            MouseArea {
                id: folderArea
                anchors.fill: parent
                hoverEnabled: true
                onClicked: flyout.capture.openCaptures()
            }
        }
    }
}
