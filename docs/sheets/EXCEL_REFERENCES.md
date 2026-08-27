# The Excel reference library

Same rule as the Windows 11 library: **one authentic screenshot per component, published by
Microsoft, never committed, always checksummed.** The catalogue is
`assets/refs/excel/library.json`; fetch it with

```
python3 tools/visual/fetch_references.py --library excel
python3 tools/visual/fetch_references.py --library excel --check
```

Measurements taken from it live in `system/theme/excel-reference.json`, each next to the raw
device-pixel number it came from.

## What is admitted

* Hosted on a Microsoft domain (`support.microsoft.com`, `support.content.office.net`,
  `learn.microsoft.com`).
* **Excel for Windows desktop.** Excel for the web, Excel for macOS and Excel for iPad are *not*
  admitted as geometry references — their chrome is different and mixing them would quietly
  corrupt every number derived from them.
* The current generation where it matters: the 2023 visual refresh (Aptos Narrow, rounded ribbon
  card). Older captures are admitted only when the surface has not changed, and are labelled.

## Notes on what we were given

| Source | Verdict |
| --- | --- |
| Owner's screenshot 1 (Backstage "Good evening") | Genuine Microsoft 365 Backstage, but a marketing composite with a wallpaper and drop shadow — usable for layout, not for measurement. |
| Owner's screenshot 2 (full window, green title bar, Ideas button) | Excel for Windows, but the **classic pre-2023 ribbon**, and rehosted by a download aggregator with the title text edited. Chrome geometry is intact; the ribbon generation is old. |
| Owner's screenshot 3 | **Excel for macOS.** Not used for Windows geometry. |

## Gaps — open, not papered over

No trustworthy Microsoft-hosted desktop capture was found in this pass for:

* Backstage **Print Preview** (only the Excel-for-the-web print pane exists)
* **Excel Options** dialog, including Customize Ribbon
* the **status bar** close-up and its right-click customise menu
* the **Conditional Formatting** rules manager
* the **cell right-click context menu** (only a chart context menu, and that one looks like the
  web build)
* full-tab captures of **Data, Review, Page Layout, Formulas** — only feature-specific crops exist

Until each of those has a real reference, the corresponding Zaldros Sheets surface stays
unbuilt or is marked as unverified. Nothing is invented to fill the hole.
