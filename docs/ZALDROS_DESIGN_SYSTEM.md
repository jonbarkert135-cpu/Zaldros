# Zaldros Design System

The single source of visual truth. Implemented as QML tokens in
`shell/zaldros-shell/qml/ZaldrosTheme/Theme.qml`; anything not in a token is a bug.
Values come from Microsoft's published Windows 11 metrics plus the measured comparison in
`docs/VISUAL_FOUNDATION_RESEARCH.md` §2 — never from guesswork or from extracted Microsoft assets.

## 1. Typography — Selawik (OFL 1.1)

| Token | Size | Weight | Use |
| --- | --- | --- | --- |
| `fontCaption` | 12 px | Regular | tray, tile labels, secondary lines |
| `fontBody` | 14 px | Regular | standard UI text, menu items, list rows |
| `fontSubtitle` | 16 px | SemiBold | section headings ("Закреплено") |
| `fontTitle` | 20 px | SemiBold | page titles |

Family resolution is verified at runtime: if Selawik fails to register, the shell reports the family
it actually got rather than claiming Selawik.

## 2. Colour

| Token | Dark | Light | Use |
| --- | --- | --- | --- |
| `background` | `#202020` | `#F3F3F3` | window and page background |
| `surface` | `#2C2C2C` | `#FFFFFF` | cards, menus, flyouts |
| `surfaceElevated` | `#383838` | `#FBFBFB` | Start panel, popups over surfaces |
| `taskbarBg` | `#2B2B2B` @0.95 | `#F3F3F3` @0.95 | the panel |
| `border` | white @12 % | black @8 % | 1 px separators and outlines |
| `accent` | `#60CDFF` | `#0067C0` | selection, active indicator, toggles |
| `accentText` | `#00243D` | `#FFFFFF` | text on accent |
| `textPrimary` | `#FFFFFF` | `#1B1B1B` | body text |
| `textSecondary` | `#C8C8C8` | `#5D5D5D` | subtitles, unavailable-reason text |
| `textDisabled` | `#7A7A7A` | `#9D9D9D` | disabled controls |
| `hover` / `pressed` / `selected` | white @9 % / @5 % / @15 % | black @5 % / @8 % / @10 % | interaction states |

Rule: an unavailable control is drawn with `textDisabled` **and** its reason — never as a
decorative switch (spec PART 3, VISUAL FOUNDATION §8).

## 3. Geometry

| Token | Value |
| --- | --- |
| Spacing scale | 4 / 8 / 12 / 16 / 24 / 32 px |
| Radius | small 4 px · flyout/menu 8 px · window/Start 10 px · pill = height/2 |
| Taskbar | height 48 px · button 40 × 40 px · icon 24 px · tray icon 16 px |
| Start | 640 × 726 px · padding 32 px · pin grid 6 columns · pin icon 32 px |
| Quick settings | 360 px wide · tile 100 × 68 px · 3 columns |
| Menus | row 32 px · min width 200 px · padding 4 px |
| Window title bar | 32 px · caption buttons 46 × 32 px (Windows 11 proportions) |

## 4. Elevation and transparency

One shadow token (`shadow`, black @40 %) drawn at three offsets by the components that need it —
buttons 1 px, menus 4 px, Start and windows 8 px. A three-token Material-style elevation scale was
considered and rejected: Windows 11 uses far fewer elevation levels than Material, and the extra
tokens would have had one user each.

Panels sit on an **opaque base** plus a translucent tint (0.92 taskbar, 0.96 flyouts). Real acrylic
blur arrives with KWin; until then translucency is deliberately conservative, because a
half-transparent panel over live windows is unreadable — a defect this project already shipped once.

## 5. Motion

| Token | Duration | Use |
| --- | --- | --- |
| `animFast` | 75 ms | hover and press feedback (value measured in Win11-gtk-theme) |
| `animNormal` | 180 ms | flyout open/close, tile states |
| `animSlow` | 250 ms | Start open, theme switch |

Easing: standard `OutCubic`; entrances ease out, exits ease in.

## 6. Iconography

Fluent UI System Icons (MIT), 20 px regular grid, recoloured to the current token colour at render
time. Application icons come from the host icon theme by freedesktop name; when the theme has no
icon, the shell falls back to a lettered tile rather than showing a wrong icon.

## 7. States

focus = 2 px `accent` ring at 2 px offset (always visible, keyboard navigation is not optional) ·
hover / pressed / selected per the colour table · disabled = 45 % opacity **plus** a reason string.
