import QtQuick
import ZaldrosTheme

// Windows 11 context menu, measured from assets/refs/win11_context_menu.png: 8 px radius, 4 px
// padding, 32 px items with a 4 px hover plate inset by 4 px, 16 px leading glyph column,
// shortcut text and submenu chevrons on the right, a hairline separator, and a drop shadow.
Item {
    id: menu
    property bool shown: false
    property var items: []
    // Windows 11 sizes a context menu to its content and never clips a label under its shortcut;
    // win11-reference.json → context_menu.min_width is the measured floor, not a fixed width.
    property int minWidth: 300
    property int maxWidth: 560
    property int contentWidth: 0
    readonly property int menuWidth: Math.max(minWidth, Math.min(maxWidth, contentWidth))
    // index of the row whose submenu is open, -1 for none
    property int openSubmenu: -1
    signal itemChosen(string action)

    onShownChanged: if (!shown) openSubmenu = -1
    onItemsChanged: measureContent()
    Component.onCompleted: measureContent()

    // Geometry of one row, in the same order the delegate lays it out below.
    readonly property int rowLeftMargin:  12
    readonly property int rowGlyph:       16
    readonly property int rowGlyphGap:    14
    readonly property int rowTrailingGap: 24   // measured gap between a label and its shortcut
    readonly property int rowRightMargin: 12

    TextMetrics {
        id: labelMetrics
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontCaption + 1
    }
    TextMetrics {
        id: shortcutMetrics
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontCaption
    }

    /* Widest row wins: left margin + glyph column + label + gap + shortcut/chevron + right margin.
       Run #35 found the desktop menu drawing "Показать дополнительные параметры" straight through
       "Shift+F10" because the width was pinned at 300 whatever the language. */
    function measureContent() {
        var widest = 0;
        for (var i = 0; i < items.length; i++) {
            var entry = items[i];
            if (!entry || entry.separator === true)
                continue;
            labelMetrics.text = entry.label ? entry.label : "";
            var row = rowLeftMargin + labelMetrics.width + rowTrailingGap + rowRightMargin;
            if (entry.glyph)
                row += rowGlyph + rowGlyphGap;
            if (entry.shortcut) {
                shortcutMetrics.text = entry.shortcut;
                row += shortcutMetrics.width;
            } else if (entry.submenu === true) {
                row += 12;
            }
            widest = Math.max(widest, row);
        }
        contentWidth = Math.ceil(widest);
    }

    width: menuWidth
    height: column.implicitHeight + Theme.menuPadding * 2
    visible: opacity > 0.01
    opacity: shown ? 1 : 0
    scale: shown ? 1 : 0.97
    enabled: shown
    transformOrigin: Item.TopLeft
    Behavior on opacity { NumberAnimation { duration: Theme.animFast } }
    Behavior on scale { NumberAnimation { duration: Theme.animFast; easing.type: Easing.OutCubic } }

    // drop shadow, drawn as offset plates (no GPU effects in the headless renderer)
    Repeater {
        model: [{ m: 8, o: 0.18 }, { m: 4, o: 0.20 }, { m: 1, o: 0.22 }]
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

    // Opaque base under the acrylic tint: without it whatever sits behind the menu reads straight
    // through the text (a defect this shell shipped once already).
    Rectangle {
        anchors.fill: parent
        radius: Theme.radiusMedium
        color: Theme.background
    }

    Rectangle {
        anchors.fill: parent
        radius: Theme.radiusMedium
        color: Theme.dark ? "#f52c2c2c" : "#f8fbfbfb"
        border.width: 1
        border.color: Theme.borderStrong

        Column {
            id: column
            anchors.fill: parent
            anchors.margins: Theme.menuPadding
            spacing: 0
            Repeater {
                model: menu.items
                delegate: Item {
                    width: column.width
                    height: modelData.separator ? 7 : Theme.menuItemHeight
                    Rectangle {
                        visible: modelData.separator === true
                        anchors.centerIn: parent
                        width: parent.width - 8
                        height: 1
                        color: Theme.border
                    }
                    Rectangle {
                        visible: !modelData.separator
                        anchors.fill: parent
                        anchors.leftMargin: 1
                        anchors.rightMargin: 1
                        radius: Theme.radiusSmall
                        color: itemArea.pressed ? Theme.pressed
                               : (itemArea.containsMouse ? Theme.hover : "transparent")
                    }
                    Row {
                        visible: !modelData.separator
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.left: parent.left
                        anchors.leftMargin: 12
                        spacing: 14
                        SysIcon {
                            glyph: modelData.glyph ? modelData.glyph : ""
                            visible: glyph !== ""
                            width: 16; height: 16
                            color: Theme.textPrimary
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Text {
                            text: modelData.label ? modelData.label : ""
                            color: Theme.textPrimary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontCaption + 1
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }
                    SysIcon {
                        visible: !modelData.separator && modelData.submenu === true
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.right: parent.right
                        anchors.rightMargin: 12
                        glyph: "chevron-right"
                        width: 12; height: 12
                        color: Theme.textSecondary
                    }
                    Text {
                        visible: !modelData.separator && modelData.shortcut !== undefined
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.right: parent.right
                        anchors.rightMargin: 12
                        text: modelData.shortcut ? modelData.shortcut : ""
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontCaption
                    }
                    MouseArea {
                        id: itemArea
                        anchors.fill: parent
                        hoverEnabled: true
                        enabled: !modelData.separator
                        onEntered: menu.openSubmenu = modelData.submenu === true ? index : -1
                        onClicked: {
                            if (modelData.submenu === true)
                                menu.openSubmenu = menu.openSubmenu === index ? -1 : index;
                            else
                                menu.itemChosen(modelData.action ? modelData.action : "");
                        }
                    }

                    // Windows 11 opens the submenu flush with the parent row, slightly overlapping.
                    // QML refuses to instantiate a component inside itself, so the submenu is
                    // loaded by file name at runtime instead of nested statically.
                    Loader {
                        id: submenuLoader
                        active: menu.openSubmenu === index && modelData.submenu === true
                        source: "ContextMenu.qml"
                        x: menu.menuWidth - 6
                        y: -Theme.menuPadding
                        z: 10
                        onLoaded: {
                            item.minWidth = 220;
                            item.items = modelData.children !== undefined ? modelData.children : [];
                            item.shown = true;
                            item.itemChosen.connect(menu.itemChosen);
                        }
                    }
                }
            }
        }
    }
}
