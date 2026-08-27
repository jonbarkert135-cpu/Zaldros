import QtQuick
import ZaldrosTheme

// Win+V — the clipboard history flyout.
//
// Geometry measured from the maintainer's own Windows 11 capture (2026-08-26, 125 % scale): the
// panel is 448 px wide in that capture = 360 logical, the same width as every other Windows 11
// flyout; the cards are 96 px tall with an 8 px gutter = 76 + 8 logical. Recorded in
// system/theme/win11-reference.json → clipboard and re-checked by tools/visual/parity.py.
//
// Everything here is backed by the real clipboard (zaldros_shell/clipboard.py +
// model.ClipboardModel): the cards are what was actually copied in this session, the pin survives
// a reboot, and "Очистить все" removes everything except the pinned entries — exactly Windows'
// rule. The emoji / GIF / kaomoji tabs of the Windows panel are deliberately *not* drawn: a tab
// that opens nothing is the kind of decoration this project does not ship.
Item {
    id: flyout
    objectName: "clipboardFlyout"

    property bool shown: false
    property real baseY: 0
    property var clipboard: null

    width: Theme.clipboardWidth
    height: Math.min(Theme.clipboardMaxHeight, body.implicitHeight + 2 * Theme.clipboardPadding)
    visible: opacity > 0.01
    opacity: shown ? 1 : 0
    y: shown ? baseY : baseY + 16
    enabled: shown
    Behavior on opacity { NumberAnimation { duration: Theme.animNormal; easing.type: Easing.OutCubic } }
    Behavior on y { NumberAnimation { duration: Theme.animNormal; easing.type: Easing.OutCubic } }

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
        anchors.margins: Theme.clipboardPadding
        spacing: 12

        // --- header: title and "Очистить все" ---------------------------------------------
        Item {
            width: parent.width
            height: 32

            Row {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                spacing: 8
                SysIcon {
                    glyph: "copy"; width: 16; height: 16
                    anchors.verticalCenter: parent.verticalCenter
                    color: Theme.textPrimary
                }
                Text {
                    text: "Буфер обмена"
                    anchors.verticalCenter: parent.verticalCenter
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSubtitle
                    color: Theme.textPrimary
                }
            }

            Rectangle {
                id: clearButton
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                width: clearLabel.implicitWidth + 24
                height: 32
                radius: Theme.radiusSmall
                color: clearArea.pressed ? Theme.pressed
                       : (clearArea.containsMouse ? Theme.hover : Theme.surface)
                border.width: 1
                border.color: Theme.border
                opacity: flyout.clipboard && !flyout.clipboard.empty ? 1.0 : 0.4
                Behavior on color { ColorAnimation { duration: Theme.animFast } }

                Text {
                    id: clearLabel
                    anchors.centerIn: parent
                    text: "Очистить все"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontCaption
                    color: Theme.textPrimary
                }
                MouseArea {
                    id: clearArea
                    anchors.fill: parent
                    hoverEnabled: true
                    enabled: flyout.clipboard && !flyout.clipboard.empty
                    onClicked: flyout.clipboard.clearAll()
                }
            }
        }

        // --- empty state -------------------------------------------------------------------
        Column {
            width: parent.width
            spacing: 6
            visible: !flyout.clipboard || flyout.clipboard.empty

            Text {
                text: "Здесь пока пусто"
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBody
                color: Theme.textPrimary
            }
            Text {
                width: parent.width
                text: "Скопируйте текст или изображение — последние 25 записей появятся здесь."
                wrapMode: Text.WordWrap
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontCaption
                color: Theme.textSecondary
            }
        }

        // --- the history --------------------------------------------------------------------
        ListView {
            id: list
            width: parent.width
            visible: flyout.clipboard && !flyout.clipboard.empty
            height: visible ? Math.min(Theme.clipboardMaxHeight - 2 * Theme.clipboardPadding - 44,
                                       contentHeight) : 0
            model: flyout.clipboard
            spacing: Theme.clipboardCardGap
            clip: true
            boundsBehavior: Flickable.StopAtBounds

            delegate: Rectangle {
                width: list.width
                height: Theme.clipboardCardHeight
                radius: Theme.radiusMedium
                color: cardArea.pressed ? Theme.pressed
                       : (cardArea.containsMouse ? Theme.surfaceElevated : Theme.surfaceCard)
                Behavior on color { ColorAnimation { duration: Theme.animFast } }

                MouseArea {
                    id: cardArea
                    anchors.fill: parent
                    hoverEnabled: true
                    // Windows puts the entry back on the clipboard and pastes it into the focused
                    // field; we can honestly do the first half, so that is what the card does.
                    onClicked: flyout.clipboard.applyRow(index)
                }

                // image entries show the bitmap, text entries show the text
                Image {
                    visible: kind === "image"
                    source: kind === "image" ? path : ""
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.leftMargin: 12
                    width: 132
                    height: Theme.clipboardCardHeight - 16
                    fillMode: Image.PreserveAspectFit
                    asynchronous: false
                }
                Text {
                    visible: kind !== "image"
                    text: preview
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.margins: 12
                    width: parent.width - 60
                    maximumLineCount: 3
                    elide: Text.ElideRight
                    wrapMode: Text.Wrap
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontCaption
                    color: Theme.textPrimary
                }

                IconButton {
                    glyph: "more"
                    tooltip: "Удалить"
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 6
                    onTriggered: flyout.clipboard.deleteRow(index)
                }
                IconButton {
                    glyph: "pin"
                    tooltip: pinned ? "Открепить" : "Закрепить"
                    opacity: pinned ? 1.0 : (cardArea.containsMouse ? 0.8 : 0.45)
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    anchors.margins: 6
                    onTriggered: flyout.clipboard.pinRow(index)
                }
            }
        }
    }
}
