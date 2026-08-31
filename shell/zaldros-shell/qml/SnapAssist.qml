import QtQuick
import ZaldrosTheme

// Windows 11 Snap Assist: right after a window is snapped into one zone, the free part of the
// screen fills with thumbnails of the other open windows, so the second half of the layout can be
// filled with one click instead of a second drag.
//
// Behaviour is Microsoft's, quoted from support.microsoft.com/en-us/windows/experience/
// snap-your-windows: "When you snap a window to one side of the screen, Snap Assist will display
// thumbnails of your other open windows, allowing you to quickly choose which window to snap to
// the other side."
//
// Geometry: Microsoft publishes no Snap Assist capture with a known display scale, so the padding,
// gap and caption band here are DERIVED from the shell's own Fluent spacing scale (Theme.snapAssist*)
// and are deliberately not stored in win11-reference.json as measurements. What *is* pinned to the
// reference is the frame this grid lives in: it covers exactly the zones the chosen layout leaves
// free, which come from the measured layout fractions.
Item {
    id: root

    // The free rectangle, as fractions {x, y, w, h} of the work area.
    property var zone: ({ x: 0.5, y: 0, w: 0.5, h: 1 })
    // [{ id, name, glyph }] — the other open windows, in taskbar order.
    property var candidates: []

    signal windowChosen(string id)
    signal dismissed()

    readonly property int columns: root.candidates.length <= 1 ? 1 : 2
    readonly property int rows: Math.ceil(root.candidates.length / root.columns)
    // The grid fills the free zone, but a card never stretches past a 16:9 preview plus its caption
    // — Windows keeps the thumbnails in the aspect of the screen they represent and centres what is
    // left over, instead of smearing two windows over a tall strip.
    readonly property real availableWidth:
        (root.width - Theme.snapAssistPadding * 2
         - Theme.snapAssistGap * (root.columns - 1)) / root.columns
    readonly property real availableHeight:
        (root.height - Theme.snapAssistPadding * 2
         - Theme.snapAssistGap * (root.rows - 1)) / Math.max(root.rows, 1)
    readonly property real cellWidth:
        Math.max(Math.min(root.availableWidth,
                          (root.availableHeight - Theme.snapAssistCaption) * 16 / 9), 0)
    readonly property real cellHeight: root.cellWidth * 9 / 16 + Theme.snapAssistCaption

    // The dimmed plate over the free zone. Windows blurs the desktop behind it; we have no blur
    // effect in the QML shell yet (that needs a KWin C++ effect), so this is a flat scrim.
    Rectangle {
        objectName: "snapAssistScrim"
        anchors.fill: parent
        color: Theme.snapAssistScrim

        MouseArea {
            anchors.fill: parent
            // Clicking past the thumbnails leaves the first window snapped and the rest alone,
            // which is what dismissing Snap Assist does in Windows.
            onClicked: root.dismissed()
        }
    }

    Grid {
        objectName: "snapAssistGrid"
        anchors.centerIn: parent
        columns: root.columns
        rowSpacing: Theme.snapAssistGap
        columnSpacing: Theme.snapAssistGap

        Repeater {
            model: root.candidates.length

            delegate: Rectangle {
                id: card
                objectName: "snapAssistCard" + index
                readonly property var entry: root.candidates[index]
                width: root.cellWidth
                height: root.cellHeight
                radius: Theme.radiusMedium
                color: hover.containsMouse ? Theme.surfaceElevated : Theme.surfaceAcrylic
                border.width: 1
                border.color: hover.containsMouse ? Theme.accent : Theme.border

                // The window preview. A real thumbnail needs the compositor's surface texture,
                // which the QML shell cannot reach; until the KWin side hands one over this is the
                // app's own icon on the window plate, not a fake screenshot.
                Rectangle {
                    objectName: "snapAssistPreview" + index
                    x: 1; y: 1
                    width: card.width - 2
                    height: card.height - Theme.snapAssistCaption - 1
                    radius: Theme.radiusMedium
                    color: Theme.surface

                    SysIcon {
                        anchors.centerIn: parent
                        glyph: card.entry.glyph
                        width: 40
                        height: 40
                        color: Theme.textSecondary
                    }
                }

                Row {
                    x: 12
                    height: Theme.snapAssistCaption
                    anchors.bottom: parent.bottom
                    spacing: 8

                    SysIcon {
                        anchors.verticalCenter: parent.verticalCenter
                        glyph: card.entry.glyph
                        width: 16
                        height: 16
                        color: Theme.textPrimary
                    }

                    Text {
                        objectName: "snapAssistTitle" + index
                        anchors.verticalCenter: parent.verticalCenter
                        text: card.entry.name
                        elide: Text.ElideRight
                        width: Math.max(card.width - 48, 0)
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBody
                        color: Theme.textPrimary
                    }
                }

                MouseArea {
                    id: hover
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: root.windowChosen(card.entry.id)
                }
            }
        }
    }
}
