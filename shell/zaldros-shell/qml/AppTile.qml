import QtQuick
import ZaldrosTheme

// One application icon. Uses the host icon theme when it really has an icon for this app
// (zaldros_shell/icons.py), and falls back to a lettered tile — never a copy of a Microsoft
// product icon, never a wrong icon silently substituted.
Item {
    id: tile
    property string label: "?"
    property string iconName: ""
    property string glyph: ""     // Fluent glyph used when there is no themed app icon
    property color baseColor: Theme.accent
    property bool dim: false
    opacity: dim ? 0.45 : 1.0

    Image {
        id: themed
        anchors.fill: parent
        source: tile.iconName ? "image://zaldrosicon/app/" + tile.iconName : ""
        sourceSize.width: Math.round(width * 2)
        sourceSize.height: Math.round(height * 2)
        asynchronous: false
        fillMode: Image.PreserveAspectFit
        smooth: true
        visible: status === Image.Ready
    }

    Rectangle {
        anchors.fill: parent
        visible: !themed.visible
        radius: Math.round(width * 0.22)
        gradient: Gradient {
            GradientStop { position: 0.0; color: Qt.lighter(tile.baseColor, 1.22) }
            GradientStop { position: 1.0; color: Qt.darker(tile.baseColor, 1.15) }
        }
        SysIcon {
            anchors.centerIn: parent
            visible: tile.glyph !== ""
            glyph: tile.glyph
            color: "#ffffff"
            width: Math.round(parent.width * 0.55)
            height: width
        }
        Text {
            anchors.centerIn: parent
            visible: tile.glyph === ""
            text: tile.label
            color: "#ffffff"
            font.family: Theme.fontFamily
            font.pixelSize: Math.round(parent.height * 0.45)
            font.weight: Font.DemiBold
        }
    }
}
