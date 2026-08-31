import QtQuick
import ZaldrosTheme

// Windows 11 snap bar: drag a window to the top edge of the screen and a bar drops down with the
// same six layout thumbnails as the Win+Z flyout, under a hint line and the Win+Z badge. Dropping
// (here: clicking) a zone snaps the dragged window into it.
//
// Geometry: the strip is the flyout's, measured at 100 % scale. The header band comes from
// Microsoft's own snap-bar capture, normalised by the thumbnail strip height because that shot's
// display scale is not published — see win11-reference.json → snap_bar / sources.snap_bar.
Item {
    id: root

    signal zoneChosen(int layout, int zone, var zoneRect)

    width: strip.width
    height: strip.height

    SnapLayouts {
        id: strip
        objectName: "snapBarLayouts"
        namePrefix: "snapBar"
        topInset: Theme.snapBarHeader
        onZoneChosen: function (layout, zone, zoneRect) {
            root.zoneChosen(layout, zone, zoneRect);
        }
    }

    // --- header band -------------------------------------------------------------------------
    Item {
        x: Theme.snapPadding
        y: Theme.snapPadding
        width: root.width - Theme.snapPadding * 2
        height: Theme.snapBarHeader

        Row {
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            spacing: 10

            SysIcon {
                anchors.verticalCenter: parent.verticalCenter
                glyph: "desktop"
                width: 16
                height: 16
                color: Theme.textPrimary
            }

            Text {
                objectName: "snapBarHint"
                anchors.verticalCenter: parent.verticalCenter
                text: "Перетащите окно сюда, чтобы разместить его на экране"
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBody
                color: Theme.textPrimary
            }
        }

        // The Win+Z reminder Windows draws at the right end of the same band.
        Row {
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            spacing: 6

            Rectangle {
                anchors.verticalCenter: parent.verticalCenter
                width: 26; height: 26
                radius: Theme.radiusSmall
                color: Theme.surfaceElevated
                border.width: 1
                border.color: Theme.borderStrong
                SysIcon {
                    anchors.centerIn: parent
                    glyph: "grid"
                    width: 14; height: 14
                    color: Theme.textPrimary
                }
            }

            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: "+"
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBody
                color: Theme.textSecondary
            }

            Rectangle {
                anchors.verticalCenter: parent.verticalCenter
                width: 26; height: 26
                radius: Theme.radiusSmall
                color: Theme.surfaceElevated
                border.width: 1
                border.color: Theme.borderStrong
                Text {
                    anchors.centerIn: parent
                    text: "Z"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontCaption
                    color: Theme.textPrimary
                }
            }
        }
    }
}
