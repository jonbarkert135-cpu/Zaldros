pragma Singleton
import QtQuick

// Bedrock Shell design tokens. Values are our own, chosen to match the *proportions and behaviour*
// observed in Windows 11 — no Microsoft assets, colours sampled from our own reference screenshot
// only as general dark-theme values (spec PART 1 §2).
QtObject {
    readonly property int    taskbarHeight:   48
    readonly property int    iconSize:        24
    readonly property int    buttonSize:      40
    readonly property int    cornerRadius:    8
    readonly property int    startWidth:      640
    readonly property int    startHeight:     700
    readonly property int    startRadius:     10

    readonly property color  taskbarBg:       "#e6202020"
    readonly property color  surface:         "#f22b2b2b"
    readonly property color  surfaceAlt:      "#33ffffff"
    readonly property color  hover:           "#22ffffff"
    readonly property color  pressed:         "#33ffffff"
    readonly property color  accent:          "#4cc2ff"
    readonly property color  text:            "#ffffff"
    readonly property color  textDim:         "#c8c8c8"
    readonly property color  stroke:          "#1affffff"

    readonly property int    animFast:        120
    readonly property int    animNormal:      180
    readonly property string fontFamily:      "Noto Sans"
}
