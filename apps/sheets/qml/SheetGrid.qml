// The grid. Row height, column width, header sizes and colours all come from ref.grid /
// ref.palette — system/theme/excel-reference.json, measured from Microsoft's own captures.
// Cell contents come from the engine through gridModel; this file computes nothing.
import QtQuick

// Typing goes straight to the engine: the in-cell editor and the formula bar both call
// book.commit(), which calls Workbook.set_input() and redraws with what the engine answered.
// Nothing here decides whether «=SUM(A1:A2)» is a formula — Calc does.
Item {
    id: sheetArea
    focus: true

    // The cell being edited, or -1: Excel's own two modes, «ready» and «edit».
    property int editingRow: -1
    property int editingColumn: -1

    function beginEdit(row, column, initial) {
        book.select(row, column);
        sheetArea.editingRow = row;
        sheetArea.editingColumn = column;
        cellEditor.text = initial === undefined ? gridModel.cellFormula(row, column) : initial;
        cellEditor.forceActiveFocus();
        cellEditor.cursorPosition = cellEditor.text.length;
    }

    function commitEdit(advance) {
        if (sheetArea.editingRow < 0)
            return;
        var row = sheetArea.editingRow;
        var column = sheetArea.editingColumn;
        sheetArea.editingRow = -1;
        sheetArea.editingColumn = -1;
        book.select(row, column);
        book.commit(cellEditor.text);
        if (advance)
            book.select(Math.min(row + 1, sheetArea.rows - 1), column);
        sheetArea.forceActiveFocus();
    }

    function cancelEdit() {
        sheetArea.editingRow = -1;
        sheetArea.editingColumn = -1;
        sheetArea.forceActiveFocus();
    }

    Keys.onPressed: function (event) {
        if (sheetArea.editingRow >= 0)
            return;
        var row = book.selectedRow;
        var column = book.selectedColumn;
        if (event.key === Qt.Key_Up)          { book.select(Math.max(row - 1, 0), column); event.accepted = true; }
        else if (event.key === Qt.Key_Down)   { book.select(Math.min(row + 1, sheetArea.rows - 1), column); event.accepted = true; }
        else if (event.key === Qt.Key_Left)   { book.select(row, Math.max(column - 1, 0)); event.accepted = true; }
        else if (event.key === Qt.Key_Right || event.key === Qt.Key_Tab)
                                              { book.select(row, Math.min(column + 1, sheetArea.columns - 1)); event.accepted = true; }
        else if (event.key === Qt.Key_F2)     { sheetArea.beginEdit(row, column); event.accepted = true; }
        else if (event.key === Qt.Key_Delete) { book.commit(""); event.accepted = true; }
        else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter)
                                              { book.select(Math.min(row + 1, sheetArea.rows - 1), column); event.accepted = true; }
        else if (event.text.length > 0 && event.text >= " ") {
            // Typing over a cell replaces it, as in Excel — F2 edits in place instead.
            sheetArea.beginEdit(row, column, event.text);
            event.accepted = true;
        }
    }
    readonly property var g: ref.grid
    readonly property var pal: book.light ? ref.palette.light : ref.palette.dark
    readonly property int columns: Math.max(1, Math.ceil((width - g.row_header_width)
                                                          / g.column_width))
    readonly property int rows: Math.max(1, Math.floor((height - g.column_header_height)
                                                       / g.row_height))

    Rectangle { anchors.fill: parent; color: pal.grid }

    // corner box
    Rectangle {
        x: 0; y: 0
        width: g.row_header_width; height: g.column_header_height
        color: pal.header
        Canvas {                                  // the little triangle Excel draws there
            anchors.fill: parent
            onPaint: {
                var c = getContext("2d");
                c.reset();
                c.fillStyle = pal.text;
                c.globalAlpha = 0.55;
                c.beginPath();
                c.moveTo(width - 3, height - 3);
                c.lineTo(width - 3, 5);
                c.lineTo(5, height - 3);
                c.closePath();
                c.fill();
            }
        }
    }

    // column headers
    Row {
        x: g.row_header_width; y: 0
        Repeater {
            model: sheetArea.columns
            delegate: Rectangle {
                required property int index
                width: g.column_width; height: g.column_header_height
                color: index === book.selectedColumn ? pal.header_selected : pal.header
                Text {
                    anchors.centerIn: parent
                    text: gridModel.columnName(index)
                    color: pal.text; font.family: theme.family; font.pixelSize: 12
                }
                Rectangle { anchors { right: parent.right; top: parent.top; bottom: parent.bottom }
                            width: 1; color: pal.gridline }
            }
        }
    }

    // row headers
    Column {
        x: 0; y: g.column_header_height
        Repeater {
            model: sheetArea.rows
            delegate: Rectangle {
                required property int index
                width: g.row_header_width; height: g.row_height
                color: index === book.selectedRow ? pal.header_selected : pal.header
                Text {
                    anchors.centerIn: parent
                    text: index + 1
                    color: pal.text; font.family: theme.family; font.pixelSize: 12
                }
                Rectangle { anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
                            height: 1; color: pal.gridline }
            }
        }
    }

    // cells
    Column {
        x: g.row_header_width; y: g.column_header_height
        Repeater {
            model: sheetArea.rows
            delegate: Row {
                required property int index
                readonly property int rowIndex: index
                Repeater {
                    model: sheetArea.columns
                    delegate: Rectangle {
                        required property int index
                        width: g.column_width; height: g.row_height
                        color: "transparent"
                        Rectangle { anchors { right: parent.right; top: parent.top
                                              bottom: parent.bottom }
                                    width: 1; color: pal.gridline }
                        Rectangle { anchors { left: parent.left; right: parent.right
                                              bottom: parent.bottom }
                                    height: 1; color: pal.gridline }
                        Text {
                            anchors {
                                left: parent.left; right: parent.right
                                verticalCenter: parent.verticalCenter
                                leftMargin: 4; rightMargin: 4
                            }
                            horizontalAlignment: gridModel.cellIsNumeric(rowIndex, index)
                                                 ? Text.AlignRight : Text.AlignLeft
                            elide: Text.ElideRight
                            text: gridModel.cellText(rowIndex, index)
                            color: "#191919"
                            font.family: theme.family; font.pixelSize: 13
                        }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: {
                                book.select(rowIndex, index);
                                sheetArea.forceActiveFocus();
                            }
                            onDoubleClicked: sheetArea.beginEdit(rowIndex, index)
                        }
                    }
                }
            }
        }
    }

    // the selected cell
    Rectangle {
        x: g.row_header_width + book.selectedColumn * g.column_width
        y: g.column_header_height + book.selectedRow * g.row_height
        width: g.column_width; height: g.row_height
        color: "transparent"
        border.width: g.active_cell_border
        border.color: pal.accent
        Rectangle {                       // the fill handle
            width: 5; height: 5; color: pal.accent
            anchors { right: parent.right; bottom: parent.bottom; margins: -2 }
        }
    }

    // --- the in-cell editor ---------------------------------------------------------------
    Rectangle {
        objectName: "cellEditor"
        visible: sheetArea.editingRow >= 0
        x: g.row_header_width + sheetArea.editingColumn * g.column_width
        y: g.column_header_height + sheetArea.editingRow * g.row_height
        width: g.column_width; height: g.row_height
        color: "#ffffff"
        border.width: g.active_cell_border
        border.color: pal.accent
        TextInput {
            id: cellEditor
            anchors { fill: parent; leftMargin: 4; rightMargin: 4 }
            verticalAlignment: TextInput.AlignVCenter
            color: "#191919"
            font.family: theme.family
            font.pixelSize: 13
            clip: true
            Keys.onPressed: function (event) {
                if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                    sheetArea.commitEdit(true);
                    event.accepted = true;
                } else if (event.key === Qt.Key_Escape) {
                    sheetArea.cancelEdit();
                    event.accepted = true;
                } else if (event.key === Qt.Key_Tab) {
                    sheetArea.commitEdit(false);
                    book.select(book.selectedRow, book.selectedColumn + 1);
                    event.accepted = true;
                }
            }
        }
    }
}
