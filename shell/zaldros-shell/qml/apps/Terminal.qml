import QtQuick
import QtQuick.Controls
import ZaldrosTheme
import ".."

// Командная строка, собранная по снимку настоящей: **одна** полоса вверху, где вкладка, «+» и
// стрелка профилей стоят прямо в заголовке окна рядом с кнопками управления — а не двумя рядами,
// как было. Вкладки живут в AppWindow (`tabs`), поэтому здесь остались только панели и сетка.
//
// Every character comes from a real pty (zaldros_backend/terminal.py). Nothing here is simulated:
// the prompt, the colours and the exit code are the shell's own.
Item {
    id: terminal
    property var model: null
    property bool dropdownOpen: false

    readonly property int cellWidth: 8
    readonly property int cellHeight: 17
    readonly property var panes: model ? model.panes : []

    function resizeToWindow() {
        if (!terminal.model)
            return;
        var columns = Math.max(20, Math.floor(grid.width / terminal.cellWidth));
        var rows = Math.max(5, Math.floor(grid.height / terminal.cellHeight));
        terminal.model.resize(columns, rows);
    }

    onWidthChanged: resizeToWindow()
    onHeightChanged: resizeToWindow()

    Component.onCompleted: {
        if (terminal.model && terminal.model.tabCount === 0)
            terminal.model.openTab("");
        resizeToWindow();
    }

    Rectangle { anchors.fill: parent; color: "#0c0c0c" }

    // --- profile dropdown ---------------------------------------------------------------------
    Rectangle {
        id: dropdown
        objectName: "terminalProfiles"
        visible: terminal.dropdownOpen
        z: 5
        x: 200
        y: 2
        width: 260
        height: profileColumn.height + 8
        radius: Theme.radiusMedium
        color: Theme.surfaceAcrylic
        border.width: 1
        border.color: Theme.border

        Column {
            id: profileColumn
            y: 4
            width: parent.width
            Repeater {
                model: terminal.model ? terminal.model.profiles : []
                delegate: Rectangle {
                    width: dropdown.width; height: Theme.menuItemHeight
                    color: profileHover.containsMouse ? Theme.surfaceCard : "transparent"
                    Text {
                        x: 12
                        anchors.verticalCenter: parent.verticalCenter
                        text: modelData.name + (modelData.default ? "   (по умолчанию)" : "")
                        color: Theme.textPrimary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontCaption
                    }
                    MouseArea {
                        id: profileHover
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: {
                            terminal.model.openTab(modelData.command);
                            terminal.dropdownOpen = false;
                        }
                    }
                }
            }
        }
    }

    // --- panes -------------------------------------------------------------------------------
    Row {
        id: grid
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 0
        spacing: 6

        Repeater {
            model: terminal.panes
            delegate: Rectangle {
                width: (grid.width - (terminal.panes.length - 1) * 6) / terminal.panes.length
                height: grid.height
                color: "#0c0c0c"
                border.width: terminal.panes.length > 1 && modelData.active ? 1 : 0
                border.color: Theme.accent

                Column {
                    id: screen
                    anchors.fill: parent
                    anchors.leftMargin: 10
                    anchors.topMargin: 6
                    Repeater {
                        model: modelData.lines
                        delegate: Row {
                            height: terminal.cellHeight
                            Repeater {
                                model: modelData
                                delegate: Text {
                                    text: modelData.text
                                    color: modelData.inverse ? modelData.background
                                                             : modelData.foreground
                                    font.family: "monospace"
                                    font.pixelSize: 13
                                    font.bold: modelData.bold
                                    font.underline: modelData.underline
                                    textFormat: Text.PlainText
                                }
                            }
                        }
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        terminal.model.selectPane(index);
                        terminal.forceActiveFocus();
                    }
                }
            }
        }
    }

    // --- keyboard -------------------------------------------------------------------------------
    focus: true
    Keys.onPressed: function (event) {
        if (!terminal.model)
            return;
        var control = (event.modifiers & Qt.ControlModifier) !== 0;
        var shift = (event.modifiers & Qt.ShiftModifier) !== 0;
        if (control && shift && event.key === Qt.Key_T) { terminal.model.openTab(""); event.accepted = true; return; }
        if (control && shift && event.key === Qt.Key_W) { terminal.model.closeTab(terminal.model.activeTab); event.accepted = true; return; }
        if (control && shift && event.key === Qt.Key_D) { terminal.model.splitPane(); event.accepted = true; return; }
        if (control && shift && event.key === Qt.Key_C) { terminal.model.copy(); event.accepted = true; return; }

        // Control characters the shell expects: Ctrl+C is \x03, Ctrl+D is \x04, and so on.
        if (control && !shift && event.key >= Qt.Key_A && event.key <= Qt.Key_Z) {
            terminal.model.send(String.fromCharCode(event.key - Qt.Key_A + 1));
            event.accepted = true;
            return;
        }
        var sequences = {};
        sequences[Qt.Key_Return] = "\r";
        sequences[Qt.Key_Enter] = "\r";
        sequences[Qt.Key_Backspace] = "\u007f";
        sequences[Qt.Key_Tab] = "\t";
        sequences[Qt.Key_Escape] = "\u001b";
        sequences[Qt.Key_Up] = "\u001b[A";
        sequences[Qt.Key_Down] = "\u001b[B";
        sequences[Qt.Key_Right] = "\u001b[C";
        sequences[Qt.Key_Left] = "\u001b[D";
        sequences[Qt.Key_Home] = "\u001b[H";
        sequences[Qt.Key_End] = "\u001b[F";
        sequences[Qt.Key_Delete] = "\u001b[3~";
        if (sequences[event.key] !== undefined) {
            terminal.model.send(sequences[event.key]);
            event.accepted = true;
            return;
        }
        if (event.text.length > 0) {
            terminal.model.send(event.text);
            event.accepted = true;
        }
    }
}
