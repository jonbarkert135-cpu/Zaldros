import QtQuick
import ZaldrosTheme

// A Zaldros application window: 8 px rounded corners, 32 px Mica title bar, 46x32 caption buttons
// in Windows order with the #c42b1c close hover, a layered drop shadow and distinct active and
// inactive states. Dragging, minimise, maximise and close are real: the window manager in
// Shell.qml owns the state and this component reports the user's intent.
Item {
    id: win

    property string title: "Окно"
    property string iconName: ""
    property string iconGlyph: "window"
    // Windows 11 Settings has no app icon in its title bar: a back arrow sits where the icon
    // would be. Apps that keep an icon leave these two alone.
    property bool showIcon: true
    property bool showBack: false
    signal backRequested()
    property bool active: true
    property bool maximized: false
    // Snapped into a layout zone (Windows 11 snap layouts). A snapped window is not draggable:
    // its geometry belongs to the zone until it is maximised or restored, exactly like a maximised
    // one. Double-clicking the title bar takes it out of the zone.
    property bool snapped: false
    property bool showTitleText: true
    // Windows 11 apps with tabs (Explorer) put the tab strip *in* the title bar and grow it to
    // 40 px; everything else keeps the 32 px bar. [{ title, glyph }]
    // Tabs drawn in the title bar. Explorer passes decorative ones; the command prompt passes
    // live ones and listens to these signals, which is why a tab without an `active` field is
    // treated as active — the old look must not shift by one pixel.
    property var tabs: []
    property bool showTabMenu: false
    signal tabActivated(int index)
    signal tabCloseRequested(int index)
    signal newTabRequested()
    signal tabMenuRequested()
    readonly property int barHeight: tabs.length > 0 ? Theme.tabStripHeight : Theme.titleBarHeight
    property int workAreaHeight: parent ? parent.height - Theme.taskbarHeight : height
    // children declared inside an AppWindow land in the body, below the title bar
    default property alias content: body.data

    signal activateRequested()
    signal minimiseRequested()
    signal maximiseToggled()
    signal closeRequested()
    // Windows 11 opens the snap layouts flyout when the pointer rests on the maximise button.
    // The window cannot draw it (it would be clipped by the frame), so it reports the anchor point
    // — the bottom centre of the button in the shell's coordinates — and the shell draws it.
    signal snapMenuRequested(real anchorX, real anchorY)
    // Windows 11 drops the snap bar down when a dragged window reaches the top edge of the screen.
    // The window only reports whether it is up there; the shell owns the bar.
    signal snapBarRequested(bool atTopEdge)
    // Windows 11 snaps a window when it is *dropped* against a screen edge, and shows a
    // translucent pane where it would land while the pointer is still down. The window only
    // reports the pointer in the shell's coordinates and the release; the shell decides the zone.
    signal dragPointMoved(real sx, real sy)
    signal dragDropped()
    readonly property bool dragging: titleDrag.drag.active
    onDraggingChanged: win.snapBarRequested(win.dragging && win.y <= Theme.snapBarTrigger)
    onYChanged: if (win.dragging) win.snapBarRequested(win.y <= Theme.snapBarTrigger)

    // --- drop shadow: three offset plates, because MultiEffect needs a GPU we cannot assume ----
    Repeater {
        model: win.active ? [{ m: 10, o: 0.16 }, { m: 6, o: 0.20 }, { m: 2, o: 0.24 }]
                          : [{ m: 6, o: 0.10 }, { m: 2, o: 0.12 }]
        delegate: Rectangle {
            anchors.fill: parent
            anchors.margins: -modelData.m
            anchors.topMargin: -modelData.m + 2
            radius: Theme.radiusMedium + modelData.m
            color: "#000000"
            opacity: modelData.o
            z: -1
        }
    }

    Rectangle {
        id: frame
        anchors.fill: parent
        // Rounded on every window, maximised included: the maintainer asked for it on 2026-08-26
        // and it is what the shell's own windows look like against the wallpaper.
        radius: Theme.radiusMedium
        color: Theme.appBackground
        border.width: 1
        border.color: win.active ? Theme.borderStrong : Theme.border
        clip: true

        // --- title bar -------------------------------------------------------------------------
        Rectangle {
            id: titleBar
            objectName: "titleBar"
            width: parent.width
            height: win.barHeight
            color: win.active ? Theme.mica : Qt.darker(Theme.mica, 1.08)

            MouseArea {
                id: titleDrag
                anchors.fill: parent
                anchors.rightMargin: captionRow.width
                onPressed: win.activateRequested()
                onDoubleClicked: win.maximiseToggled()
                onPositionChanged: function (mouse) {
                    if (!titleDrag.drag.active || !win.parent) return;
                    var point = titleDrag.mapToItem(win.parent, mouse.x, mouse.y);
                    win.dragPointMoved(point.x, point.y);
                }
                // Always reported: the shell acts only if it has a pending zone for this window,
                // and drag.active is already false by the time the release arrives.
                onReleased: win.dragDropped()
                drag.target: (win.maximized || win.snapped) ? null : win
                drag.minimumX: 0
                drag.minimumY: 0
                drag.maximumX: win.parent ? win.parent.width - win.width : 0
                drag.maximumY: win.workAreaHeight - win.barHeight
            }

            Row {
                visible: win.tabs.length === 0
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                anchors.leftMargin: Theme.titleLeftMargin
                spacing: 10
                Rectangle {
                    visible: win.showBack
                    width: 28; height: 28; radius: Theme.radiusSmall
                    anchors.verticalCenter: parent.verticalCenter
                    color: backHover.containsMouse ? Theme.hover : "transparent"
                    SysIcon {
                        anchors.centerIn: parent
                        glyph: "arrow-left"
                        width: 14; height: 14
                        color: win.active ? Theme.textPrimary : Theme.textSecondary
                    }
                    MouseArea {
                        id: backHover
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: win.backRequested()
                    }
                }
                SysIcon {
                    visible: win.showIcon
                    width: Theme.titleIcon
                    height: Theme.titleIcon
                    anchors.verticalCenter: parent.verticalCenter
                    glyph: win.iconGlyph
                    color: win.active ? Theme.textPrimary : Theme.textSecondary
                }
                Text {
                    visible: win.showTitleText
                    anchors.verticalCenter: parent.verticalCenter
                    text: win.title
                    color: win.active ? Theme.textPrimary : Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontCaption
                }
            }

            Row {
                id: tabRow
                visible: win.tabs.length > 0
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                anchors.leftMargin: 8
                spacing: 4
                Repeater {
                    model: win.tabs
                    delegate: Rectangle {
                        id: tabItem
                        readonly property bool isActive: modelData.active === undefined
                                                         ? true : modelData.active
                        width: Math.min(240, tabLabel.implicitWidth + 68)
                        height: 32
                        radius: Theme.radiusMedium
                        color: tabItem.isActive ? Theme.appBackground
                             : (tabArea.containsMouse ? Theme.hover : "transparent")
                        border.width: tabItem.isActive ? 1 : 0
                        border.color: Theme.border
                        MouseArea {
                            id: tabArea
                            anchors.fill: parent
                            hoverEnabled: true
                            onClicked: win.tabActivated(index)
                        }
                        Row {
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.left: parent.left
                            anchors.leftMargin: 10
                            spacing: 8
                            SysIcon {
                                glyph: modelData.glyph ? modelData.glyph : "folder"
                                width: 16; height: 16
                                color: Theme.accent
                                anchors.verticalCenter: parent.verticalCenter
                            }
                            Text {
                                id: tabLabel
                                anchors.verticalCenter: parent.verticalCenter
                                text: modelData.title
                                color: Theme.textPrimary
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontCaption
                                elide: Text.ElideRight
                            }
                        }
                        SysIcon {
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.right: parent.right
                            anchors.rightMargin: 8
                            glyph: "close"; width: 10; height: 10
                            color: Theme.textSecondary
                            MouseArea {
                                anchors.fill: parent
                                anchors.margins: -6
                                onClicked: win.tabCloseRequested(index)
                            }
                        }
                    }
                }
                IconButton {
                    glyph: "add"
                    tooltip: "Новая вкладка"
                    anchors.verticalCenter: parent.verticalCenter
                    onTriggered: win.newTabRequested()
                }
                // The caret that opens the profile list, as in Windows Terminal.
                Item {
                    visible: win.showTabMenu
                    width: visible ? 22 : 0
                    height: 32
                    anchors.verticalCenter: parent.verticalCenter
                    Text {
                        anchors.centerIn: parent
                        text: "\u2304"
                        color: Theme.textSecondary
                        font.pixelSize: 12
                    }
                    MouseArea { anchors.fill: parent; onClicked: win.tabMenuRequested() }
                }
            }

            Row {
                id: captionRow
                objectName: "captionButtons"
                anchors.right: parent.right
                anchors.top: parent.top
                Repeater {
                    model: [{ g: "minimize", a: "min" },
                            { g: "maximize", a: "max" },
                            { g: "close", a: "close" }]
                    delegate: Item {
                        width: Theme.captionWidth
                        height: win.barHeight
                        Rectangle {
                            anchors.fill: parent
                            color: !btnArea.containsMouse ? "transparent"
                                   : (modelData.a === "close" ? Theme.closeHover
                                      : (btnArea.pressed ? Theme.pressed : Theme.hover))
                        }
                        SysIcon {
                            anchors.centerIn: parent
                            glyph: modelData.g
                            width: Theme.captionGlyph
                            height: Theme.captionGlyph
                            color: btnArea.containsMouse && modelData.a === "close"
                                   ? "#ffffff"
                                   : (win.active ? Theme.textPrimary : Theme.textSecondary)
                        }
                        // Windows 11 opens the snap flyout after the pointer has rested on the
                        // maximise button; a click before that still maximises, as it should.
                        Timer {
                            id: snapDelay
                            interval: 400
                            onTriggered: {
                                var point = captionRow.mapToItem(win.parent, 0, 0);
                                win.snapMenuRequested(point.x + btnArea.parent.x
                                                      + Theme.captionWidth / 2,
                                                      point.y + win.barHeight);
                            }
                        }

                        MouseArea {
                            id: btnArea
                            anchors.fill: parent
                            hoverEnabled: true
                            onEntered: if (modelData.a === "max") snapDelay.restart()
                            onExited: snapDelay.stop()
                            onClicked: {
                                snapDelay.stop();
                                if (modelData.a === "min") win.minimiseRequested();
                                else if (modelData.a === "max") win.maximiseToggled();
                                else win.closeRequested();
                            }
                        }
                    }
                }
            }
        }

        Item {
            id: body
            anchors.top: titleBar.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
        }

        // clicking anywhere in the window raises it, as every desktop expects
        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.LeftButton
            propagateComposedEvents: true
            z: -1
            onPressed: function(mouse) { win.activateRequested(); mouse.accepted = false }
        }
    }
}
