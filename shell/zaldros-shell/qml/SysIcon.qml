import QtQuick
import ZaldrosTheme

// Vector system icons drawn by us. No third-party icon pack is vendored yet (see
// docs/VISUAL_THIRD_PARTY.md — Fluent UI System Icons, MIT, is the chosen set once the build host
// has network access), so these are original strokes in the same 24 px grid and 1.5 px weight.
Canvas {
    id: root
    property string glyph: "wifi"
    property color color: Theme.textPrimary
    property real weight: 1.5
    property bool dim: false
    width: 16
    height: 16
    opacity: dim ? 0.45 : 1.0
    onGlyphChanged: requestPaint()
    onColorChanged: requestPaint()
    onWidthChanged: requestPaint()

    onPaint: {
        var ctx = getContext("2d");
        ctx.reset();
        var s = width, u = s / 16;
        ctx.strokeStyle = color; ctx.fillStyle = color;
        ctx.lineWidth = weight * u; ctx.lineCap = "round"; ctx.lineJoin = "round";

        if (glyph === "wifi") {
            for (var i = 0; i < 3; ++i) {
                ctx.beginPath();
                ctx.arc(8 * u, 12 * u, (3 + i * 3) * u, Math.PI * 1.25, Math.PI * 1.75);
                ctx.stroke();
            }
            ctx.beginPath(); ctx.arc(8 * u, 12 * u, 1.1 * u, 0, Math.PI * 2); ctx.fill();
        } else if (glyph === "ethernet") {
            ctx.strokeRect(2.5 * u, 5.5 * u, 11 * u, 7 * u);
            for (var e = 0; e < 3; ++e) {
                ctx.beginPath();
                ctx.moveTo((5 + e * 3) * u, 5.5 * u);
                ctx.lineTo((5 + e * 3) * u, 12.5 * u);
                ctx.stroke();
            }
        } else if (glyph === "volume") {
            ctx.beginPath();
            ctx.moveTo(3 * u, 6 * u); ctx.lineTo(5.5 * u, 6 * u); ctx.lineTo(8.5 * u, 3 * u);
            ctx.lineTo(8.5 * u, 13 * u); ctx.lineTo(5.5 * u, 10 * u); ctx.lineTo(3 * u, 10 * u);
            ctx.closePath(); ctx.fill();
            ctx.beginPath(); ctx.arc(9 * u, 8 * u, 3 * u, -Math.PI / 3, Math.PI / 3); ctx.stroke();
            ctx.beginPath(); ctx.arc(9 * u, 8 * u, 5 * u, -Math.PI / 3, Math.PI / 3); ctx.stroke();
        } else if (glyph === "battery") {
            ctx.strokeRect(2 * u, 5.5 * u, 11 * u, 5.5 * u);
            ctx.fillRect(13.5 * u, 7.2 * u, 1.2 * u, 2.2 * u);
        } else if (glyph === "bluetooth") {
            ctx.beginPath();
            ctx.moveTo(5 * u, 5 * u); ctx.lineTo(11 * u, 11 * u); ctx.lineTo(8 * u, 14 * u);
            ctx.lineTo(8 * u, 2 * u); ctx.lineTo(11 * u, 5 * u); ctx.lineTo(5 * u, 11 * u);
            ctx.stroke();
        } else if (glyph === "chevron-up") {
            ctx.beginPath(); ctx.moveTo(4 * u, 10 * u); ctx.lineTo(8 * u, 6 * u);
            ctx.lineTo(12 * u, 10 * u); ctx.stroke();
        } else if (glyph === "chevron-right") {
            ctx.beginPath(); ctx.moveTo(6 * u, 4 * u); ctx.lineTo(10 * u, 8 * u);
            ctx.lineTo(6 * u, 12 * u); ctx.stroke();
        } else if (glyph === "search") {
            ctx.beginPath(); ctx.arc(7 * u, 7 * u, 4.2 * u, 0, Math.PI * 2); ctx.stroke();
            ctx.beginPath(); ctx.moveTo(10.2 * u, 10.2 * u); ctx.lineTo(14 * u, 14 * u); ctx.stroke();
        } else if (glyph === "bell") {
            ctx.beginPath();
            ctx.moveTo(4 * u, 11 * u); ctx.lineTo(4 * u, 7.5 * u);
            ctx.arc(8 * u, 7.5 * u, 4 * u, Math.PI, 0);
            ctx.lineTo(12 * u, 11 * u); ctx.lineTo(4 * u, 11 * u); ctx.stroke();
            ctx.beginPath(); ctx.arc(8 * u, 12.6 * u, 1.4 * u, 0, Math.PI); ctx.stroke();
        } else if (glyph === "power") {
            ctx.beginPath(); ctx.arc(8 * u, 9 * u, 5 * u, -Math.PI * 0.35, Math.PI * 1.35); ctx.stroke();
            ctx.beginPath(); ctx.moveTo(8 * u, 2 * u); ctx.lineTo(8 * u, 8 * u); ctx.stroke();
        } else if (glyph === "user") {
            ctx.beginPath(); ctx.arc(8 * u, 6 * u, 3 * u, 0, Math.PI * 2); ctx.stroke();
            ctx.beginPath(); ctx.arc(8 * u, 15 * u, 5.5 * u, Math.PI, 0); ctx.stroke();
        } else if (glyph === "folder") {
            ctx.beginPath();
            ctx.moveTo(2 * u, 12.5 * u); ctx.lineTo(2 * u, 4 * u); ctx.lineTo(6.5 * u, 4 * u);
            ctx.lineTo(8 * u, 6 * u); ctx.lineTo(14 * u, 6 * u); ctx.lineTo(14 * u, 12.5 * u);
            ctx.closePath(); ctx.stroke();
        } else if (glyph === "brightness") {
            ctx.beginPath(); ctx.arc(8 * u, 8 * u, 3 * u, 0, Math.PI * 2); ctx.stroke();
            for (var k = 0; k < 8; ++k) {
                var a = k * Math.PI / 4;
                ctx.beginPath();
                ctx.moveTo(8 * u + Math.cos(a) * 5 * u, 8 * u + Math.sin(a) * 5 * u);
                ctx.lineTo(8 * u + Math.cos(a) * 6.5 * u, 8 * u + Math.sin(a) * 6.5 * u);
                ctx.stroke();
            }
        } else if (glyph === "night") {
            ctx.beginPath();
            ctx.arc(9 * u, 8 * u, 5.5 * u, Math.PI * 0.35, Math.PI * 1.45);
            ctx.arc(6.5 * u, 8 * u, 6.5 * u, Math.PI * 1.35, Math.PI * 0.45, true);
            ctx.stroke();
        } else if (glyph === "cast") {
            ctx.strokeRect(2.5 * u, 4 * u, 11 * u, 7.5 * u);
            ctx.beginPath(); ctx.moveTo(5.5 * u, 14 * u); ctx.lineTo(10.5 * u, 14 * u); ctx.stroke();
        } else if (glyph === "accessibility") {
            ctx.beginPath(); ctx.arc(8 * u, 3.5 * u, 1.6 * u, 0, Math.PI * 2); ctx.stroke();
            ctx.beginPath(); ctx.moveTo(3 * u, 7 * u); ctx.lineTo(13 * u, 7 * u); ctx.stroke();
            ctx.beginPath(); ctx.moveTo(8 * u, 7 * u); ctx.lineTo(8 * u, 10 * u);
            ctx.lineTo(5.5 * u, 14 * u); ctx.moveTo(8 * u, 10 * u); ctx.lineTo(10.5 * u, 14 * u);
            ctx.stroke();
        } else if (glyph === "vpn") {
            ctx.beginPath();
            ctx.moveTo(8 * u, 2 * u); ctx.lineTo(13.5 * u, 4.5 * u); ctx.lineTo(13.5 * u, 8.5 * u);
            ctx.bezierCurveTo(13.5 * u, 12 * u, 11 * u, 13.5 * u, 8 * u, 14.5 * u);
            ctx.bezierCurveTo(5 * u, 13.5 * u, 2.5 * u, 12 * u, 2.5 * u, 8.5 * u);
            ctx.lineTo(2.5 * u, 4.5 * u); ctx.closePath(); ctx.stroke();
        } else if (glyph === "close" || glyph === "minimize" || glyph === "maximize") {
            if (glyph === "close") {
                ctx.beginPath(); ctx.moveTo(4 * u, 4 * u); ctx.lineTo(12 * u, 12 * u);
                ctx.moveTo(12 * u, 4 * u); ctx.lineTo(4 * u, 12 * u); ctx.stroke();
            } else if (glyph === "minimize") {
                ctx.beginPath(); ctx.moveTo(4 * u, 8 * u); ctx.lineTo(12 * u, 8 * u); ctx.stroke();
            } else {
                ctx.strokeRect(4.5 * u, 4.5 * u, 7 * u, 7 * u);
            }
        }
    }
}
