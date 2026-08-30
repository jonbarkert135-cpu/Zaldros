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

    // No binding for currentIndex here: `grid` lives inside the Instantiator's delegate, which is
    // a separate component scope, and KWin writes this property itself before showing the box
    // (tabboxhandler.cpp: item->setCurrentIndex(indexRow)). The grid pushes its selection back in
    // onCurrentIndexChanged below, exactly as kwin's own thumbnail_grid layout does.

    // Proof the layout is loaded at all: without it, a boot cannot tell an unloadable QML file
    // from a tabbox that never opened.
    Component.onCompleted: console.log("ZALDROS-SWITCHER tabbox layout loaded")
    onVisibleChanged: console.log("ZALDROS-SWITCHER tabbox visible=" + tabBox.visible)

    Instantiator {
        active: tabBox.visible

        delegate: Window {
            // A borderless full-screen surface: Windows 11 dims the whole desktop behind the
            // switcher rather than showing a small dialog, and KWin treats this as an internal
            // window, so nothing else in the session has to cooperate.
            // Not Qt.Popup: an internal popup wants a transient parent and a keyboard grab, and
            // KWin never puts it in the scene; Qt.X11BypassWindowManagerHint means nothing to a
            // Wayland session. Measured in runs #29-#34 (nothing drawn) and again in run #39 with
            // the same flags on the script's own window.
            flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus
            visible: true

            // One line per appearance, so a boot can tell "the layout never loaded" from "it
            // loaded and KWin drew nothing". Same prefix as the script: selftest.py greps it.
            Component.onCompleted: console.log("ZALDROS-SWITCHER tabbox surface visible=" + visible
                + " geometry=" + x + "," + y + " " + width + "x" + height)
            color: "transparent"
            x: tabBox.screenGeometry.x
            y: tabBox.screenGeometry.y
            width: tabBox.screenGeometry.width
            height: tabBox.screenGeometry.height

            Rectangle {
                anchors.fill: parent
                color: tabBox.backdropColour

                // Windows 11 does not scatter the cards on the dimmed desktop: they sit on one
                // rounded translucent panel. Ours is the theme surface colour at the same alpha as
                // the shell's flyouts; a real acrylic blur would need the Plasma QML stack that a
                // Zaldros session does not run (ADR-0008), so the panel is tinted, not blurred.
                Rectangle {
                    id: panel
                    anchors.centerIn: parent
                    width: cards.width + 2 * grid.panelPadding
                    height: cards.height + 2 * grid.panelPadding
                    radius: tabBox.cornerRadius * 2
                    color: Qt.rgba(tabBox.surfaceColour.r, tabBox.surfaceColour.g,
                                   tabBox.surfaceColour.b, 0.92)
                    border.width: 1
                    border.color: Qt.rgba(1, 1, 1, 0.08)

                    FocusScope {
                        id: cards
                        anchors.centerIn: parent
                        focus: true
                        width: Math.min(grid.contentWidthHint, tabBox.screenGeometry.width * 0.85)
                        height: Math.min(grid.contentHeightHint, tabBox.screenGeometry.height * 0.75)

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
                            readonly property int cardWidth: 300
                            readonly property int cardHeight: 188
                            readonly property int captionHeight: 30
                            readonly property int gutter: 16
                            readonly property int panelPadding: 20
                            readonly property int columns: Math.max(1, Math.min(count,
                                Math.floor(tabBox.screenGeometry.width * 0.85 / cellWidth)))
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
                                    color: index === grid.currentIndex ? Qt.rgba(1, 1, 1, 0.16)
                                                                       : (card.containsMouse ? Qt.rgba(1, 1, 1, 0.08)
                                                                                             : "transparent")
                                    border.width: index === grid.currentIndex ? 2 : 0
                                    border.color: tabBox.accentColour

                                    // Windows 11 puts the application icon left of the title on
                                    // every card. The icon comes from its own file so a missing
                                    // Kirigami module costs the icon, not the whole switcher.
                                    Row {
                                        id: caption
                                        anchors.top: parent.top
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.margins: 8
                                        height: grid.captionHeight - 8
                                        spacing: 6

                                        Loader {
                                            anchors.verticalCenter: parent.verticalCenter
                                            source: "IconBadge.qml"
                                            onLoaded: item.iconSource = model.icon
                                        }

                                        Text {
                                            anchors.verticalCenter: parent.verticalCenter
                                            width: caption.width - x
                                            text: model.caption
                                            color: tabBox.textColour
                                            elide: Text.ElideRight
                                            textFormat: Text.PlainText
                                            verticalAlignment: Text.AlignVCenter
                                        }
                                    }

                                    // Holder for the live thumbnail. It carries the card radius
                                    // for the gap around the thumbnail; Qt's clip is rectangular,
                                    // so the thumbnail's own corners stay square — rounding them
                                    // would need a shader mask, which is not worth it here.
                                    Rectangle {
                                        anchors.top: caption.bottom
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.bottom: parent.bottom
                                        anchors.margins: 8
                                        anchors.topMargin: 0
                                        radius: tabBox.cornerRadius
                                        color: "transparent"

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
}
