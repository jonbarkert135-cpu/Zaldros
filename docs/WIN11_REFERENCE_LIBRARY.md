# The Windows 11 reference library

The parity loop in `docs/VISUAL_PARITY_PROCESS.md` starts with a REFERENCE. Until now that
reference was two things: one committed Start capture and a set of screenshots the maintainer took
on his own machine, which show personal data and can never be published. Anyone else auditing a
number in `system/theme/win11-reference.json` had to take it on trust.

This library fixes that. It is a catalogue of **36 authentic Windows 11 screenshots published by
Microsoft itself**, covering every UI state Zaldros implements.

- Catalogue: `assets/refs/win11/library.json`
- Fetch into a local cache: `python3 tools/visual/fetch_references.py`
- Re-derive geometry from it: `python3 tools/visual/measure_library.py`

## Why the images are not in the repository

They are Microsoft's copyright. The catalogue stores the URL, the page it appears on, the pixel
dimensions and the sha256 of every file; `fetch_references.py` downloads them into
`assets/refs/win11/cache/` (gitignored) and refuses to continue if a checksum does not match, so a
reference that quietly changed upstream can never poison a measurement.

## What counts as authentic

Windows 11 is the single most imitated desktop on the internet: most "Windows 11 screenshots" in
search results are Linux themes, Rectify11 builds, concept renders or fan mockups. Two rules keep
those out:

1. **Microsoft-hosted only.** Every entry is served from `learn.microsoft.com`,
   `support.microsoft.com`, `blogs.windows.com` (or its `winblogs`/`msftstories` asset CDNs) or
   `news.microsoft.com`. No third-party blog, no image search, no aggregator.
2. **Named evidence per entry.** Each record carries an `evidence` line saying what the capture
   shows and why it is a real session — for example the Quick Settings capture still carries the
   "Evaluation copy. Build 22553" watermark of a running Insider build, and the annotated Start
   capture is the one Microsoft itself labels in its Start layout documentation.

Marketing composites are kept, but labelled: the 2021 press-kit and blog hero images are upscaled
(2100–4000 px wide) and were never rendered at those sizes, so they are layout references, not
measurement sources.

## Coverage

| State | Entries | Example |
| --- | --- | --- |
| desktop | 4 | press-start-light, explorer-tabs |
| taskbar | 8 | quick-settings, press-notifications, settings-taskbar |
| start | 7 | start-support, start-annotated, start-folders |
| search | 2 | search-flyout (taskbar search with Top/Apps/Documents/Web) |
| settings | 8 | settings-start, settings-taskbar, settings-windows-update, settings-dark |
| file_explorer | 4 | explorer-100pct, explorer-folder-previews, explorer-menu-acrylic |
| context_menu | 6 | context-menu-2021, context-menu-2026, settings-context-menu |
| quick_settings | 1 | quick-settings (Win+A flyout at 150 %) |
| notifications | 3 | press-notifications, settings-notifications, widgets |
| window_decorations | 4 | titlebar-overview, titlebar-tabs, task-manager-dark |
| dark_mode | 6 | press-start-dark, settings-dark, task-manager-dark |
| light_mode | 5 | explorer-100pct, press-settings |
| dialogs | 1 | dialog-run (Run dialog with Mica) |
| multiple_windows | 3 | snap-bar-2022, context-menu-click-to-do |
| snap_layouts | 3 | snap-bar-2025, snap-layouts-flyout, snap-bar-2022 |

## Display scale: the part that decides whether a screenshot is measurable

A screenshot is only worth measuring if its display scale is known, and Microsoft never states it.
Two captures in the library prove their own scale:

- **`quick-access-update2.png`** — File Explorer. Its three caption glyphs sit 45.5 px apart, and a
  Windows 11 caption button is 46 logical px, so the capture is at **100 %**: pixels are logical
  pixels. This is the most useful public reference in the set.
- **`color-profile-quick-settings.png`** — the Quick Settings flyout, panel 536 px wide against a
  360 logical px panel, i.e. **150 %**.

`tools/visual/measure_library.py` measures both and compares the result with the committed
reference. Today, 8 of 8 measurements agree — including four numbers that had only ever been
measured from the maintainer's private captures:

| Metric | Public library | `win11-reference.json` |
| --- | --- | --- |
| caption button width | 45.5 | 46 |
| context menu item height | 31.0 | 32 |
| quick settings panel width | 360.0 | 360 |
| quick settings padding | 24.2 | 25 |
| quick settings tile width | 95.6 | 95 |
| quick settings tile height | 47.8 | 47 |
| quick settings tile gap | 13.5 | 13 |

## What the comparison found

Rendering the seven Zaldros states next to these references (run #35) produced one defect that the
geometry parity tool could not see, because it is a text-layout defect, not a component-size one:

- **The desktop context menu drew its label through its shortcut.** `ContextMenu.qml` pinned the
  menu at 300 px whatever the content, so the Russian row "Показать дополнительные параметры"
  overlapped "Shift+F10". Windows 11 sizes a menu to its widest row. Fixed: the menu now measures
  its rows with `TextMetrics` and treats 300 px as a floor, `context_menu.min_width`. Gate:
  `shell/zaldros-shell/tests/test_context_menu_fit.py` renders the menu and fails when the gutter
  before the trailing text drops below 8 px.

Open questions the library raises but does not settle (they need the maintainer's call, so nothing
was changed):

- Explorer's navigation pane measures **240 px at 100 %** in `quick-access-update2.png`; the token
  is 190. The pane is user-resizable, so the capture may simply show a widened pane.
- The Explorer details-view row pitch measures **30 px at 100 %**; the token is 32.

## Caption button glyphs — measured, 2026-08-28

A magnified real Windows 11 title-bar capture (Wikimedia Commons,
`20231209 18 08 05-Greenshot Titlebar buttons.png`, 706 x 224, CC licence on the file page) gives
the glyphs at a size where a pixel grid cannot hide anything. Measured with PIL:

| what | in the capture | button = 46 px | our theme |
| --- | --- | --- | --- |
| button pitch | 239 px | 46.0 | 46 |
| minimize bar width | 52 px | 10.0 | 10 |
| minimize bar thickness | 5 px | 0.96 | 1 |
| maximize square | 52 x 53 px | 10.0 x 10.2 | 10 x 10 |
| maximize corner radius | ~8 px | ~1.5 | 1.5 |
| close X box | 52 x 52 px | 10.0 | 10 |

All three glyphs are the same 52 px wide: the minimize bar is exactly as long as the X is wide.
That is the number to quote when the bar looks "too short" — it is not, it is 10 px like the rest.

## Adding an entry

1. Find the screenshot on a Microsoft page. Prefer the un-resized original: WordPress serves
   `name-1024x640.png`, the full image is `name.png`.
2. Add a record to `assets/refs/win11/library.json` with `id`, `states`, `url`, `page`, `width`,
   `height`, `bytes`, `sha256`, `windows_version`, `display_scale` (only when it can be proven) and
   an `evidence` sentence.
3. Run `python3 tools/visual/fetch_references.py` — it verifies the checksum you recorded.
4. If the scale is provable, teach `tools/visual/measure_library.py` to measure it, so the number
   becomes a check instead of a claim.
