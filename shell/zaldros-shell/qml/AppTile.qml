import QtQuick
import ZaldrosTheme

// One application icon: coloured rounded square with the app's initial. Placeholder artwork until a
// licensed icon set is vendored (docs/VISUAL_THIRD_PARTY.md) — deliberately simple, never a copy of
// a Microsoft product icon.
Item {
    id: tile
    property string label: "?"
    property color baseColor: Theme.accent
    property bool dim: false
    opacity: dim ? 0.45 : 1.0

    Rectangle {
        anchors.fill: parent
        radius: Math.round(width * 0.22)
        gradient: Gradient {
            GradientStop { position: 0.0; color: Qt.lighter(tile.baseColor, 1.22) }
            GradientStop { position: 1.0; color: Qt.darker(tile.baseColor, 1.15) }
        }
        Text {
            anchors.centerIn: parent
            text: tile.label
            color: "#ffffff"
            font.family: Theme.fontFamily
            font.pixelSize: Math.round(parent.height * 0.45)
            font.weight: Font.DemiBold
        }
    }
}
