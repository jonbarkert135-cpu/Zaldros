import QtQuick
import ZaldrosTheme

// System icons from Fluent UI System Icons (Microsoft, MIT), vendored in assets/icons/fluent and
// recoloured by zaldros_shell/icons.py. See docs/VISUAL_LICENSE_AUDIT.md.
Image {
    id: root
    property string glyph: "wifi"
    property color color: Theme.textPrimary
    property bool dim: false
    width: 16
    height: 16
    opacity: dim ? 0.45 : 1.0
    // ponytail: the provider caches per name+colour; distinct themes mean a handful of entries.
    source: glyph ? "image://zaldrosicon/" + glyph + "?" + encodeURIComponent(color) : ""
    sourceSize.width: Math.round(width * 2)     // crisp on HiDPI
    sourceSize.height: Math.round(height * 2)
    asynchronous: false          // headless renders grab one frame; async icons would miss it
    fillMode: Image.PreserveAspectFit
    smooth: true
    mipmap: true
}
