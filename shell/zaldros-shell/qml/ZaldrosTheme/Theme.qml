pragma Singleton
import QtQuick

// Zaldros Shell design tokens.
//
// Every geometry value below is measured from the Windows 11 captures in assets/refs and stored in
// system/theme/win11-reference.json (see tools/visual/measure_reference.py). tools/visual/parity.py
// re-measures the rendered shell and fails when a token drifts away from the reference, so these
// numbers are checked, not decorative.
//
// Colours are ours: Windows-neutral greys and a Zaldros accent, never sampled artwork.
// Typography: PT Sans (SIL OFL 1.1, ParaType). Chosen by measurement against the Windows 11
// capture in assets/refs (tools/visual/font_match.py) because it must carry Cyrillic — the previous
// Selawik had none and the Russian UI silently fell back to DejaVu Sans.
QtObject {
    id: theme

    // --- theme mode -------------------------------------------------------------------------
    property bool dark: true

    // --- taskbar (win11-reference.json → taskbar) ---------------------------------------------
    readonly property int taskbarHeight:     48
    readonly property int taskbarIcon:       24
    readonly property int taskbarButton:     44   // measured button pitch of the centred group
    readonly property int taskbarButtonHeight: 40
    readonly property int trayIcon:          16
    readonly property int trayButton:        36
    readonly property int indicatorWidth:     6
    readonly property int indicatorActive:   16
    readonly property int indicatorHeight:    3
    readonly property int taskbarSearchWidth: 220
    readonly property int taskbarSearchHeight: 32
    readonly property int taskbarRightMargin: 12
    readonly property int taskbarWidgetLeft:  20   // left edge of the weather icon, measured
    readonly property int taskbarWidgetGap:   12   // icon to the two text lines

    // --- Start (win11-reference.json → start) --------------------------------------------------
    readonly property int startWidth:        640
    readonly property int startHeight:       726
    readonly property int startGap:           12
    readonly property int startPadding:       32
    readonly property int startSearchWidth:  576
    readonly property int startSearchHeight:  38
    readonly property int startPinIcon:       32
    readonly property int startCellWidth:     96
    readonly property int startCellHeight:    84
    readonly property int startColumns:        6
    readonly property int startFooterHeight:  64

    // --- windows (win11-reference.json → window / explorer) -------------------------------------
    readonly property int titleBarHeight:     32
    readonly property int tabStripHeight:     40
    readonly property int captionWidth:       46
    readonly property int captionHeight:      32
    readonly property int captionGlyph:       10
    readonly property int titleIcon:          16
    readonly property int titleLeftMargin:    12
    readonly property int navBarHeight:       48
    readonly property int commandBarHeight:   48
    readonly property int sidebarWidth:      190
    readonly property int listRowHeight:      32

    // --- flyouts ----------------------------------------------------------------------------
    readonly property int quickWidth:        360
    readonly property int notificationWidth: 360
    // Win+V (win11-reference.json → clipboard), measured from the maintainer's 125 % capture
    readonly property int clipboardWidth:    360
    readonly property int clipboardPadding:   16
    readonly property int clipboardCardHeight: 76
    readonly property int clipboardCardGap:    8
    readonly property int clipboardMaxHeight: 420

    // Win+G (win11-reference.json → game_bar), measured from the maintainer's 125 % capture:
    // panel 383 px, tiles 70 px on a 90 px pitch, 21 px padding, header 66 px, footer 82 px.
    readonly property int gameBarWidth:      306
    readonly property int gameBarPadding:     17
    readonly property int gameBarTile:        56
    readonly property int gameBarTileGap:     16
    readonly property int gameBarHeader:      53
    readonly property int gameBarFooter:      66
    // the floating bar itself: 654 x 67 px in the same capture = 523 x 54 logical,
    // middle group 279 px = 223, buttons on a 50 px = 40 pitch, active tile 40 px = 32
    readonly property int gameBarBarWidth:   523
    readonly property int gameBarBarHeight:   54
    readonly property int gameBarBarRadius:    8
    readonly property int gameBarBarButton:   40
    readonly property int gameBarBarGlyph:    20
    readonly property int gameBarBarPadding:   8
    readonly property int gameBarBarTile:     42
    readonly property int gameBarBarGap:       8
    readonly property int gameBarBarGroup:   223
    readonly property int gameBarBarGroupPadding: 24
    readonly property int flyoutGap:          12
    readonly property int menuItemHeight:     32
    readonly property int menuPadding:         4

    // --- radii --------------------------------------------------------------------------------
    readonly property int radiusSmall:         4
    readonly property int radiusMedium:        8
    readonly property int radiusLarge:        10

    // --- typography -------------------------------------------------------------------------
    // Set at startup from the vendored faces; falls back to the host default when the font failed
    // to load or cannot draw Cyrillic, so text never silently renders in a family we did not choose.
    property string fontFamily: "PT Sans"
    // Wallpaper file URL, set at startup from assets/wallpaper.
    property string wallpaper: ""
    readonly property int fontCaption:   12   // tray, labels, list rows
    readonly property int fontBody:      14   // standard UI text
    readonly property int fontSubtitle:  16
    readonly property int fontTitle:     20
    readonly property int fontPageTitle: 28   // Settings page heading, measured from the capture
    readonly property real lineHeight:   1.35

    // --- motion -----------------------------------------------------------------------------
    readonly property int animFast:   75    // Win11-gtk-theme uses the same 75 ms hover duration
    readonly property int animNormal: 180
    readonly property int animSlow:   250

    // --- colour tokens (alias tokens resolve against the active mode) ------------------------
    readonly property color background:      dark ? "#202020" : "#f3f3f3"
    readonly property color appBackground:   dark ? "#191919" : "#ffffff"   // Explorer/Settings body
    readonly property color surface:         dark ? "#2c2c2c" : "#ffffff"
    readonly property color surfaceElevated: dark ? "#383838" : "#fbfbfb"
    readonly property color surfaceCard:     dark ? "#2b2b2b" : "#fdfdfd"   // Settings row cards
    readonly property color surfaceAcrylic:  dark ? "#f7262626" : "#f9fafafa"
    readonly property color taskbarBg:       dark ? "#212121" : "#f3f3f3"   // measured, opaque
    readonly property color mica:            dark ? "#202020" : "#f5f5f5"   // title bar / tab strip
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
    readonly property color closeHover:      "#c42b1c"
}
