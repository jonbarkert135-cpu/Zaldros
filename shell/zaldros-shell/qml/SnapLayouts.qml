import QtQuick
import ZaldrosTheme

// Windows 11 snap layouts: the flyout that opens under the maximise caption button (and on Win+Z).
// Six layouts, each a thumbnail of the screen divided into zones; clicking a zone snaps the window
// that opened the flyout into that fraction of the work area.
//
// The six layouts and every number here are measured from Microsoft's own 22H2 capture
// (win11-reference.json → snap_layouts, re-derivable with tools/visual/measure_library.py):
// thumbnails 96x62 on a 14 px gap, 6 px between cells, 13 px panel padding. The zone fractions come
// out of the measured cell widths — they are not a guess about what Windows does.
Item {
    id: root

    // Zones per layout, as fractions {x, y, w, h} of the work area.
    readonly property var layouts: [
        [{ x: 0,      y: 0,   w: 0.5,    h: 1   },
         { x: 0.5,    y: 0,   w: 0.5,    h: 1   }],
        [{ x: 0,      y: 0,   w: 2 / 3,  h: 1   },
         { x: 2 / 3,  y: 0,   w: 1 / 3,  h: 1   }],
        [{ x: 0,      y: 0,   w: 0.5,    h: 1   },
         { x: 0.5,    y: 0,   w: 0.5,    h: 0.5 },
         { x: 0.5,    y: 0.5, w: 0.5,    h: 0.5 }],
        [{ x: 0,      y: 0,   w: 0.5,    h: 0.5 },
         { x: 0.5,    y: 0,   w: 0.5,    h: 0.5 },
         { x: 0,      y: 0.5, w: 0.5,    h: 0.5 },
         { x: 0.5,    y: 0.5, w: 0.5,    h: 0.5 }],
        [{ x: 0,      y: 0,   w: 1 / 3,  h: 1   },
         { x: 1 / 3,  y: 0,   w: 1 / 3,  h: 1   },
         { x: 2 / 3,  y: 0,   w: 1 / 3,  h: 1   }],
        [{ x: 0,      y: 0,   w: 0.25,   h: 1   },
         { x: 0.25,   y: 0,   w: 0.5,    h: 1   },
         { x: 0.75,   y: 0,   w: 0.25,   h: 1   }]
    ]

    signal zoneChosen(int layout, int zone, var zoneRect)

    width: Theme.snapPadding * 2 + layouts.length * Theme.snapThumbWidth
           + (layouts.length - 1) * Theme.snapThumbGap
    height: Theme.snapPadding * 2 + Theme.snapThumbHeight

    // The interior boundaries of one layout along an axis. Windows takes the cell gap out of the
    // thumbnail at each boundary, which is why a half is 45 px wide in a 96 px thumbnail and not 48.
    function boundaries(layoutIndex, axis) {
        var seen = [];
        var zones = root.layouts[layoutIndex];
        for (var i = 0; i < zones.length; ++i) {
            var edge = axis === "x" ? zones[i].x : zones[i].y;
            if (edge > 0.0001 && seen.indexOf(edge) < 0)
                seen.push(edge);
        }
        seen.sort(function (a, b) { return a - b });
        return seen;
    }

    // One cell of a thumbnail in thumbnail pixels: fraction of the content, plus the gaps the cell
    // spans over. A full-height cell next to a split column therefore stays full height.
    function cellRect(layoutIndex, zoneIndex, thumbWidth, thumbHeight) {
        var zone = root.layouts[layoutIndex][zoneIndex];
        var gap = Theme.snapCellGap;
        function span(axis, start, size, extent) {
            var edges = root.boundaries(layoutIndex, axis);
            var content = extent - gap * edges.length;
            var before = 0, inside = 0;
            for (var i = 0; i < edges.length; ++i) {
                if (edges[i] <= start + 0.0001) before += 1;
                else if (edges[i] < start + size - 0.0001) inside += 1;
            }
            return { at: Math.round(start * content) + gap * before,
                     size: Math.round(size * content) + gap * inside };
        }
        var horizontal = span("x", zone.x, zone.w, thumbWidth);
        var vertical = span("y", zone.y, zone.h, thumbHeight);
        return { x: horizontal.at, y: vertical.at,
                 width: horizontal.size, height: vertical.size };
    }

    Rectangle {
        anchors.fill: parent
        radius: Theme.radiusMedium
        color: Theme.surfaceAcrylic
        border.width: 1
        border.color: Theme.border

        Row {
            anchors.centerIn: parent
            spacing: Theme.snapThumbGap

            Repeater {
                model: root.layouts.length
                delegate: Item {
                    id: thumb
                    objectName: "snapThumb" + index
                    readonly property int layoutIndex: index
                    width: Theme.snapThumbWidth
                    height: Theme.snapThumbHeight

                    Repeater {
                        model: root.layouts[thumb.layoutIndex].length
                        delegate: Rectangle {
                            objectName: "snapZone" + thumb.layoutIndex + "_" + index
                            readonly property var cell:
                                root.cellRect(thumb.layoutIndex, index, thumb.width, thumb.height)
                            x: cell.x
                            y: cell.y
                            width: cell.width
                            height: cell.height
                            radius: Theme.radiusSmall
                            // Windows draws the cells as light plates on the dark panel; the one
                            // under the pointer takes the accent.
                            color: hover.containsMouse ? Theme.accent : Theme.surfaceElevated
                            border.width: 1
                            border.color: hover.containsMouse ? Theme.accent : Theme.borderStrong

                            MouseArea {
                                id: hover
                                anchors.fill: parent
                                hoverEnabled: true
                                onClicked: root.zoneChosen(
                                    thumb.layoutIndex, index,
                                    root.layouts[thumb.layoutIndex][index])
                            }
                        }
                    }
                }
            }
        }
    }
}
