pragma Singleton
import QtQuick

// Zaldros Shell design tokens.
//
// The geometry values follow the published Windows 11 metrics (48 px taskbar, 24 px taskbar icons,
// 32 px Start pin icons — Microsoft's own iconography guidance) so that the *proportions* feel right
// to a Windows user. The colour values are ours: neutral greys and a Zaldros accent, not sampled
// from proprietary artwork (spec PART 1 §2).
//
// Typography: Selawik is Microsoft's own SIL-OFL-licensed replacement for Segoe UI, so it is legal
// to redistribute. `fontFamily` lists it first and falls back to whatever the build host has.
QtObject {
    id: theme

    // --- theme mode -------------------------------------------------------------------------
    property bool dark: true

    // --- geometry ---------------------------------------------------------------------------
    readonly property int taskbarHeight:   48
    readonly property int taskbarIcon:     24
    readonly property int taskbarButton:   40
    readonly property int trayIcon:        16
    readonly property int startWidth:      640
    readonly property int startHeight:     726
    readonly property int startPadding:    32
    readonly property int startPinIcon:    32
    readonly property int startPinCell:    96
    readonly property int quickWidth:      360
    readonly property int radiusSmall:     4
    readonly property int radiusMedium:    8
    readonly property int radiusLarge:     10
    readonly property int menuItemHeight:  32

    // --- typography -------------------------------------------------------------------------
    // Set at startup from the vendored Selawik faces (Microsoft, SIL OFL 1.1); falls back to the
    // host default when the font failed to load, so text never silently renders in a fake family.
    property string fontFamily: "Selawik"
    // Wallpaper file URL, set at startup from assets/wallpaper.
    property string wallpaper: ""
    readonly property int fontCaption:   12   // tray, labels
    readonly property int fontBody:      14   // standard UI text
    readonly property int fontSubtitle:  16
    readonly property int fontTitle:     20
    readonly property real lineHeight:   1.35

    // --- motion -----------------------------------------------------------------------------
    readonly property int animFast:   75    // hover/press feedback; value measured in Win11-gtk-theme
    readonly property int animNormal: 180
    readonly property int animSlow:   250

    // --- colour tokens (alias tokens resolve against the active mode) ------------------------
    readonly property color background:      dark ? "#202020" : "#f3f3f3"
    readonly property color surface:         dark ? "#2c2c2c" : "#ffffff"
    readonly property color surfaceElevated: dark ? "#383838" : "#fbfbfb"
    readonly property color surfaceAcrylic:  dark ? "#f7262626" : "#f9fafafa"
    readonly property color taskbarBg:       dark ? "#f22b2b2b" : "#f2f3f3f3"
    readonly property color border:          dark ? "#1fffffff" : "#14000000"
    readonly property color borderStrong:    dark ? "#33ffffff" : "#22000000"
    readonly property color accent:          dark ? "#60cdff" : "#0067c0"
    readonly property color accentText:      dark ? "#00243d" : "#ffffff"
    readonly property color textPrimary:     dark ? "#ffffff" : "#1b1b1b"
    readonly property color textSecondary:   dark ? "#c8c8c8" : "#5d5d5d"
    readonly property color textDisabled:    dark ? "#7a7a7a" : "#9d9d9d"
    readonly property color hover:           dark ? "#17ffffff" : "#0d000000"
    readonly property color pressed:         dark ? "#0dffffff" : "#14000000"
    readonly property color selected:        dark ? "#26ffffff" : "#1a000000"
    readonly property color shadow:          "#66000000"
}
