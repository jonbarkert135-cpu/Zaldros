// The grid. Row height, column width, header sizes and colours all come from ref.grid /
// ref.palette — system/theme/excel-reference.json, measured from Microsoft's own captures.
// Cell contents come from the engine through gridModel; this file computes nothing.
import QtQuick

Item {
    id: sheetArea
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
                            onClicked: book.select(rowIndex, index)
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
}
