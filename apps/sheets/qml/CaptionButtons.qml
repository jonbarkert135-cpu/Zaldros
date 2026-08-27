// The same 46 x 32 caption buttons and 10 px glyphs the window decoration uses
// (docs/WIN11_REFERENCE_LIBRARY.md, measured off a magnified real Windows 11 capture).
import QtQuick

Row {
    property color glyphColor: "#ffffff"
    Repeater {
        model: ["minimize", "maximize", "close"]
        delegate: Item {
            required property string modelData
            width: 46; height: parent.height

            Rectangle {                       // minimize: a 10 x 1 hairline
                visible: modelData === "minimize"
                anchors.centerIn: parent
                width: 10; height: 1; color: glyphColor
            }
            Rectangle {                       // maximize: a 10 x 10 outline, 1.5 px radius
                visible: modelData === "maximize"
                anchors.centerIn: parent
                width: 10; height: 10; radius: 1.5
                color: "transparent"; border.width: 1; border.color: glyphColor
            }
            Item {                            // close: a 10 px X
                visible: modelData === "close"
                anchors.centerIn: parent
                width: 10; height: 10
                Rectangle { anchors.centerIn: parent; width: 14; height: 1
                            color: glyphColor; rotation: 45; antialiasing: true }
                Rectangle { anchors.centerIn: parent; width: 14; height: 1
                            color: glyphColor; rotation: -45; antialiasing: true }
            }
        }
    }
}
