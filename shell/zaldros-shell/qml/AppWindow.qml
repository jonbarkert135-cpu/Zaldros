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
    property bool active: true
    property bool maximized: false
    property bool showTitleText: true
    // Windows 11 apps with tabs (Explorer) put the tab strip *in* the title bar and grow it to
    // 40 px; everything else keeps the 32 px bar. [{ title, glyph }]
    property var tabs: []
    readonly property int barHeight: tabs.length > 0 ? Theme.tabStripHeight : Theme.titleBarHeight
    property int workAreaHeight: parent ? parent.height - Theme.taskbarHeight : height
    // children declared inside an AppWindow land in the body, below the title bar
    default property alias content: body.data

    signal activateRequested()
    signal minimiseRequested()
    signal maximiseToggled()
    signal closeRequested()

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
        radius: win.maximized ? 0 : Theme.radiusMedium
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
                anchors.fill: parent
                anchors.rightMargin: captionRow.width
                onPressed: win.activateRequested()
                onDoubleClicked: win.maximiseToggled()
                drag.target: win.maximized ? null : win
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
                SysIcon {
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
                        width: Math.min(240, tabLabel.implicitWidth + 68)
                        height: 32
                        radius: Theme.radiusMedium
                        color: Theme.appBackground
                        border.width: 1
                        border.color: Theme.border
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
                        }
                    }
                }
                IconButton {
                    glyph: "add"
                    tooltip: "Новая вкладка"
                    anchors.verticalCenter: parent.verticalCenter
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
                        MouseArea {
                            id: btnArea
                            anchors.fill: parent
                            hoverEnabled: true
                            onClicked: {
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
