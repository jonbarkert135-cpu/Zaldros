import QtQuick

// The Bedrock start mark. Deliberately NOT a four-pane Windows logo: that shape is Microsoft's
// trademark. Ours is three stacked slabs — "bedrock" — in the same 24 px optical size, so the
// taskbar rhythm matches Windows 11 without borrowing its identity.
Canvas {
    id: mark
    property color color: "#60cdff"
    width: 24
    height: 24
    onColorChanged: requestPaint()

    onPaint: {
        var ctx = getContext("2d");
        ctx.reset();
        var u = width / 24;
        var rows = [
            { y: 4.0, inset: 3.0, alpha: 1.00 },
            { y: 10.0, inset: 1.5, alpha: 0.82 },
            { y: 16.0, inset: 0.0, alpha: 0.64 }
        ];
        for (var i = 0; i < rows.length; ++i) {
            var r = rows[i];
            ctx.globalAlpha = r.alpha;
            ctx.fillStyle = color;
            var x = (3 + r.inset) * u, w = (18 - r.inset * 2) * u, h = 4.4 * u, rad = 1.2 * u;
            ctx.beginPath();
            ctx.moveTo(x + rad, r.y * u);
            ctx.lineTo(x + w - rad, r.y * u);
            ctx.quadraticCurveTo(x + w, r.y * u, x + w, r.y * u + rad);
            ctx.lineTo(x + w, r.y * u + h - rad);
            ctx.quadraticCurveTo(x + w, r.y * u + h, x + w - rad, r.y * u + h);
            ctx.lineTo(x + rad, r.y * u + h);
            ctx.quadraticCurveTo(x, r.y * u + h, x, r.y * u + h - rad);
            ctx.lineTo(x, r.y * u + rad);
            ctx.quadraticCurveTo(x, r.y * u, x + rad, r.y * u);
            ctx.closePath();
            ctx.fill();
        }
    }
}
