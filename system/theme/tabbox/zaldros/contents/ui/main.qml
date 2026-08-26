/*
 * Zaldros window switcher (Alt+Tab).
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 * Copyright (c) 2026 the Zaldros project
 *
 * Why this file exists at all: KWin 6.6 ships exactly one switcher layout, thumbnail_grid, and it
 * imports org.kde.plasma.core, org.kde.ksvg, org.kde.plasma.components and org.kde.kirigami. A
 * Zaldros session runs KWin with no Plasma shell behind it (ADR-0008), so that layout is the wrong
 * dependency and the wrong look. This one imports QtQuick and org.kde.kwin, nothing else.
 *
 * The API surface used here is KWin's, mirrored from src/tabbox/switchers/thumbnail_grid in
 * kwin v6.6.0: TabBoxSwitcher exposes model / currentIndex / visible / screenGeometry, the model
 * rows carry caption, windowId, icon, minimized and closeable, and WindowThumbnail renders a live
 * window by wId.
 *
 * Colours and radii are substituted at install time from the same tokens as the shell theme; see
 * system/theme/install-visual-theme.sh. Cell proportions are provisional: they follow the shape of
 * the Windows 11 switcher (a centred grid of 16:10 thumbnail cards with the caption above each
 * card) but its exact cell size has not been measured from a real capture yet.
 */
import QtQuick
import QtQuick.Window
import org.kde.kwin 3.0 as KWin

KWin.TabBoxSwitcher {
    id: tabBox

    readonly property color backdropColour: "@BACKDROP@"
    readonly property color surfaceColour: "@SURFACE@"
    readonly property color textColour: "@TEXT@"
    readonly property color accentColour: "@ACCENT@"
    readonly property int cornerRadius: @RADIUS@

    currentIndex: grid.currentIndex

    Instantiator {
        active: tabBox.visible

        delegate: Window {
            // A borderless full-screen surface: Windows 11 dims the whole desktop behind the
            // switcher rather than showing a small dialog, and KWin treats this as an internal
            // window, so nothing else in the session has to cooperate.
            flags: Qt.Popup | Qt.X11BypassWindowManagerHint
            visible: true
            color: "transparent"
            x: tabBox.screenGeometry.x
            y: tabBox.screenGeometry.y
            width: tabBox.screenGeometry.width
            height: tabBox.screenGeometry.height

            Rectangle {
                anchors.fill: parent
                color: tabBox.backdropColour

                FocusScope {
                    anchors.centerIn: parent
                    focus: true
                    width: Math.min(grid.contentWidthHint, parent.width * 0.9)
                    height: Math.min(grid.contentHeightHint, parent.height * 0.8)

                    GridView {
                        id: grid
                        anchors.fill: parent
                        focus: true
                        clip: true
                        model: tabBox.model
                        currentIndex: tabBox.currentIndex
                        keyNavigationWraps: true
                        highlightMoveDuration: 0

                        // 16:10 cards, the aspect the switcher is shown at on a 16:10 screen.
                        readonly property int cardWidth: 280
                        readonly property int cardHeight: 175
                        readonly property int captionHeight: 28
                        readonly property int gutter: 12
                        readonly property int columns: Math.max(1, Math.min(count,
                            Math.floor(tabBox.screenGeometry.width * 0.9 / cellWidth)))
                        readonly property int rows: Math.max(1, Math.ceil(count / columns))
                        readonly property int contentWidthHint: cellWidth * columns
                        readonly property int contentHeightHint: cellHeight * rows

                        cellWidth: cardWidth + gutter
                        cellHeight: cardHeight + captionHeight + gutter

                        delegate: MouseArea {
                            id: card
                            width: grid.cellWidth
                            height: grid.cellHeight
                            hoverEnabled: true
                            onClicked: tabBox.model.activate(index)

                            Accessible.name: model.caption
                            Accessible.role: Accessible.ListItem

                            Rectangle {
                                anchors.fill: parent
                                anchors.margins: grid.gutter / 2
                                radius: tabBox.cornerRadius
                                color: index === grid.currentIndex ? Qt.rgba(1, 1, 1, 0.10)
                                                                   : (card.containsMouse ? Qt.rgba(1, 1, 1, 0.06)
                                                                                         : "transparent")
                                border.width: index === grid.currentIndex ? 1 : 0
                                border.color: tabBox.accentColour

                                Text {
                                    id: caption
                                    anchors.top: parent.top
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    anchors.margins: 8
                                    height: grid.captionHeight - 8
                                    text: model.caption
                                    color: tabBox.textColour
                                    elide: Text.ElideRight
                                    textFormat: Text.PlainText
                                    verticalAlignment: Text.AlignVCenter
                                }

                                Item {
                                    anchors.top: caption.bottom
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    anchors.bottom: parent.bottom
                                    anchors.margins: 8
                                    anchors.topMargin: 0

                                    KWin.WindowThumbnail {
                                        anchors.fill: parent
                                        wId: model.windowId
                                    }
                                }
                            }
                        }

                        onCurrentIndexChanged: tabBox.currentIndex = grid.currentIndex

                        Keys.onPressed: function(event) {
                            if (event.key === Qt.Key_Left) grid.moveCurrentIndexLeft();
                            else if (event.key === Qt.Key_Right) grid.moveCurrentIndexRight();
                            else if (event.key === Qt.Key_Up) grid.moveCurrentIndexUp();
                            else if (event.key === Qt.Key_Down) grid.moveCurrentIndexDown();
                            else return;
                            event.accepted = true;
                        }
                    }

                    // An empty switcher is a real state (no other window is open); saying so is
                    // better than showing an empty rectangle and looking broken.
                    Text {
                        anchors.centerIn: parent
                        visible: grid.count === 0
                        text: qsTr("Нет открытых окон")
                        color: tabBox.textColour
                    }
                }
            }
        }
    }
}
