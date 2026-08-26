# Audit — the two "windows-eleven" Plasma global themes (run #29)

Question from the maintainer: *do not write visuals from scratch until it is proven that existing
Plasma work cannot be used.* Two Look-and-Feel packages by **zayronXIO** were supplied:

| Package | Version | Licence | Size on disk |
| --- | --- | --- | --- |
| `windows-eleven` (light) | 1.4.7 | GPL-3.0 | 3.3 MB |
| `windows-eleven-Dark` | 1.8.2 | GPL-3.0 | 624 KB |

## 1. What is actually inside them

Almost nothing. A Plasma Look-and-Feel package is a *configuration* package. Both archives contain
only: `metadata.desktop`, `contents/defaults` (which theme names to select), a panel build script
(`contents/layouts/org.kde.plasma.desktop-layout.js`), a plasmoid setup script, a KSplash QML
screen, previews and one wallpaper.

Every visible asset is a **KNewStuff dependency** fetched from kde-look.org at install time —
19 products for the light theme, 20 for the dark one. So the archives themselves ship no window
decoration, no colour scheme, no icons and no widgets. Each dependency was resolved through the
OCS API, downloaded and inspected (`tools/visual/kns_audit.py`).

The panel script is the clearest statement of what these themes *are*:

```js
panelbottom.addWidget("OnzeMenu")                     // Start menu plasmoid
panelbottom.addWidget("org.kde.plasma.icontasks")     // task manager plasmoid
panelbottom.addWidget("org.kde.plasma.systemtray")    // tray plasmoid
```

They are a recipe for **plasmashell**. Zaldros does not run plasmashell — the desktop is KWin plus
our own Qt/QML shell (ADR-0008) — so the recipe cannot be executed here. What *can* be reused is
the subset that plugs into KWin or into freedesktop paths and needs no Plasma session.

## 2. Component verdicts

| Component | Source | Licence | Plasma 5/6 | Needs plasmashell? | Verdict |
| --- | --- | --- | --- | --- | --- |
| **Window decoration** `Windows-Eleven-Dark` | p/1984455, 1.6.9 | GPL-3.0 | Aurorae, both | **no** | **USE DIRECTLY** — integrated |
| **Window decoration** `Windows-Eleven` (light) | p/1977804, 1.6.1 | GPL-3.0 | Aurorae, both | no | **USE DIRECTLY** — integrated (light variant) |
| **Icon theme** `Windows-Eleven` 4.8.8 (~29 700 files, 40 MB) | p/1977340 | GPL-3.0 | any desktop | no | **USE DIRECTLY** — integrated as the fallback parent of the Zaldros theme |
| Colour scheme `AbsoluteDark` / `Win11OSLight` | p/2083780, p/1563784 | GPL-3.0 (pkg) | any KDE app | no | **REFERENCE ONLY** — our `ZaldrosDark` is measured from the Windows capture; these are one `.colors` file each and are darker/bluer than the reference |
| Plasma theme `Windows-Eleven(-Dark)` (panel, widget and dialog SVGs) | p/1984464, p/1989107 | GPL-3.0 | Plasma theme API | **yes** | **REFERENCE ONLY** — the artwork only renders inside plasmashell's `PlasmaCore.FrameSvg`; our taskbar and flyouts are measured QML |
| Start menu plasmoid `OnzeMenu 11` | p/1545530 | GPL-2.0+ | plasmoid API | **yes** | **REFERENCE ONLY** — already reimplemented; useful as a behaviour reference for pinned/recent sections |
| `Present Windows Button`, weather/clock/calendar plasmoids | p/1181039 and others | GPL-2.0+/3.0 | plasmoid API | **yes** | **REIMPLEMENT** — our taskbar already carries the equivalents |
| Panel layout script | in package | GPL-3.0 | plasmashell scripting | **yes** | **REFERENCE ONLY** — read for panel geometry and tray item order |
| KSplash screen | in package | GPL-3.0 | ksplash | yes (ksplash) | **ADAPT later** — we have no splash yet; it is a plain QML file |
| SDDM themes | p/2053613, p/2060880 | GPL-3.0 | SDDM | no | **ADAPT later** — we do not ship a display manager yet |
| Cursors `Win7Build` | p/1436673 | mixed | any | no | **REJECT** — we already ship Fluent cursors (ADR-0010) and they are closer to Windows 11 |
| Widget style **Kvantum** | not in the packages | — | Qt apps | no | **CANDIDATE** — Kvantum would restyle Dolphin/Konsole widgets; needs the `qt6-style-kvantum` package plus a Win11 Kvantum theme, neither supplied here |
| Wallpapers (8 products) | various | GPL-3.0 | any | no | **REJECT** — ours are original, and several of these are photographs with unclear provenance |

## 3. Comparison: Windows 11 vs current Zaldros vs these themes

| Area | Windows 11 | Zaldros before run #29 | These Plasma themes | Best available |
| --- | --- | --- | --- | --- |
| Title bars, caption buttons | Mica title bar, buttons right, 46×32 | Breeze — visibly KDE | Aurorae SVG, close 40 px, buttons right, centred title | **Aurorae theme** (now ours) |
| Taskbar | measured | our QML, parity 34/34 | plasmoid panel, only inside plasmashell | **Zaldros** |
| Start | measured | our QML, 65-page Settings tree | OnzeMenu, needs plasmashell | **Zaldros** |
| Colours | measured from capture | measured tokens | one hand-made `.colors` | **Zaldros** |
| Icons | Windows set | 116 own SVGs, huge gaps in KDE apps | ~29 700 names, Windows 11 style | **the pack, under ours** |
| Blur / Mica | real | KWin blur effect on, unverified in a live session | same KWin effects | tie — still needs a live capture |
| Typography | Segoe UI | PT Sans (run #28c) | leaves the system font alone | **Zaldros** |
| Animations, shadows | real | KWin defaults | Aurorae `Animation=1`, `Shadow=true` | small win for Aurorae |

Conclusion: the Plasma themes are **better than us in exactly two places** — window decorations and
icon coverage — and cannot help anywhere else without dragging in the desktop shell we replaced.
Both of those are now integrated; nothing was rewritten from scratch that could have been borrowed.

## 4. What was integrated, and how it is held in place

* `assets/themes/aurorae/{Windows-Eleven,Windows-Eleven-Dark}` — vendored unmodified with
  `assets/themes/NOTICE.md`; installed to `/usr/share/aurorae/themes` and selected in `kwinrc`
  (`library=org.kde.kwin.aurorae`, `theme=__aurorae__svg__Windows-Eleven-Dark`, light variant for
  the light build).
* `kwin-style-aurorae` added to the ISO base set — verified against the Ubuntu 26.04 package
  contents index, not guessed: it provides
  `/usr/lib/x86_64-linux-gnu/qt6/plugins/org.kde.kdecoration3/org.kde.kwin.aurorae.so`.
  KWin 6 loads kdecoration3 plugins but still reads the `[org.kde.kdecoration2]` config group
  (`kwin/src/decorations/decorationbridge.cpp`).
* `assets/themes/icons/Windows-Eleven-icons-4.8.8.tar.xz` — extracted into
  `/usr/share/icons/Windows-Eleven`; the Zaldros theme now declares
  `Inherits=Windows-eleven,hicolor`, so our icons still win and the pack fills the gaps.
* `tests/test_borrowed_theme.py` — six gates: both variants complete, notice present and installed,
  kwinrc names the decoration, the ISO ships the engine, the icon pack stays a parent rather than a
  replacement, and no variant starts plasmashell.

## 5. Licence position

Everything integrated is GPL-3.0 by zayronXIO, vendored unmodified, with the notices installed into
`/usr/share/doc/zaldros/licenses/`. This matches the precedent set by ADR-0010 for the Fluent
cursor pack: borrow per slot, keep the pack identifiable, ship the licence. Nothing here is a
Microsoft asset, and no Windows file was extracted.

## 6. Open item

The verdict on how the Aurorae title bars actually look next to Windows 11 needs a **live capture
from a booted ISO** — the offscreen renderer draws our shell, not KWin decorations. That comparison
is the next step of this cycle.
