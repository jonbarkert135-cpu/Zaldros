# Zaldros Sheets — architecture

> Decision record: `docs/state/decisions/ADR-0013-sheets-runs-on-libreoffice.md`.
> Excel reference measurements: `docs/sheets/EXCEL_REFERENCES.md`.
> What the engine can and cannot do: `docs/sheets/EXCEL_FEATURE_MATRIX.md`.

```
Excel reference (measured screenshots)
        ↓
Zaldros Sheets UI      Qt 6 / QML, our own — ribbon, formula bar, grid, tabs, status bar
        ↓
Zaldros Sheets bridge  Python, apps/sheets/zaldros_sheets/ — one class per engine channel
        ↓
LibreOffice engine     soffice, headless child process — formulas, XLSX/ODS/CSV, charts
```

## The four routes, and why this one

Researched against primary sources, 2026-08-28.

| Route | What it gives | Why not / why yes |
| --- | --- | --- |
| **LOK — LibreOfficeKit** | `paintTile` renders the live document into a BGRA buffer; `postKeyEvent`/`postMouseEvent` feed input; `postUnoCommand(".uno:Bold")` drives commands; `LOK_CALLBACK_*` reports state. The seam Collabora Online and LibreOffice for Android use. | The only way to get engine-drawn pixels under our own chrome — **kept, for phase 2**. But headers require `#define LOK_USE_UNSTABLE_API`, upstream calls tiled rendering experimental, and there is no Qt/QML binding: only the GTK `lokdocview.cxx`, which is reported to render blank and crash inside a Qt process. We would write the Qt tile view ourselves. |
| **UNO / pyuno** | The document model: sheets, cells, formulas, styles, ranges, charts, filters, `.uno:` dispatch, load and store with any filter. Stable across versions by upstream's own compatibility promise. | **Chosen for phase 1.** No rendering API whatsoever — the LibreOffice developer blog states this outright — so our grid draws itself from model data. |
| **Fork core, replace Calc's UI** | Total control. | `sc/` mixes UI and model, `sfx2/` owns frame and dispatch for every LibreOffice application, and there is no supported "own frontend" seam there. A full build is hours and tens of gigabytes, on every rebase, forever. Rejected. |
| **VCL theming** | Retints stock Calc via `StyleSettings`/`QPalette`. | Cannot produce a ribbon; it is still LibreOffice's window. Rejected. |

Primary sources: <https://docs.libreoffice.org/libreofficekit.html>,
`include/LibreOfficeKit/LibreOfficeKit.hxx`,
<https://dev.blog.documentfoundation.org/2024/06/27/libreofficekit-api-in-action/>,
<https://docs.libreoffice.org/vcl.html>, <https://api.libreoffice.org/index.html>,
<https://wiki.ubuntu.com/BuildingLibreOffice>,
<https://deepwiki.com/CollaboraOnline/online/2-server-architecture>.

## Process model

`soffice` is a **child process, not a library in our address space**:

```
soffice --headless --invisible --nologo --norestore \
        -env:UserInstallation=file://<per-session profile> \
        --accept=socket,host=127.0.0.1,port=<port>;urp;StarOffice.ComponentContext
```

* The socket is bound to `127.0.0.1` only, and each session gets its own port and its own user
  profile directory, so two Sheets windows never fight over one profile lock.
* Out-of-process keeps our licence obligations to *redistributing an unmodified package*
  (`docs/sheets/LICENSING.md`) and keeps an engine crash out of our UI.
* Startup is not free. Measured in the sandbox on LibreOffice 7.4.7: the socket answers in about
  a second. The UI must show a real "starting the engine" state, never a frozen window.

## The bridge

`apps/sheets/zaldros_sheets/engine.py`

* `CalcEngine` — owns the child process and the UNO bridge. `start()`, `stop()`, context manager.
  Everything that can fail raises `EngineError` with the real reason; nothing is guessed.
* `Workbook` — one open document. `sheet_names`, `cell(...)`, `set_value`, `set_formula`,
  `save_as(path, fmt)`, `close()`.
* `Cell` — a value snapshot: `formula`, `value`, `text`, `kind` (`empty` / `number` / `text` /
  `formula`). Never a computed-by-us number.
* Filter names are the engine's own: `Calc MS Excel 2007 XML` (xlsx), `MS Excel 97` (xls),
  `calc8` (ods), `Text - txt - csv (StarCalc)` (csv).

Rule: **the engine is the source of truth.** The QML grid holds a cache of the visible window of
cells; every edit goes to the engine and the cache is refilled from what the engine reports back.
`tests/test_engine.py` asserts the round trip through the engine, not through the cache.

## Phase 2 — the tile view

Where a spreadsheet is more than text in boxes (charts, shapes, conditional-format icon sets,
print preview), we will not re-draw the engine's output; we will show it. That means the Qt
equivalent of `lokdocview.cxx`: a dedicated LOK thread, a tile cache keyed by zoom, twip↔pixel
conversion, `paintTile` into `QImage`, upload as `QSGTexture`, input forwarded through
`postMouseEvent`/`postKeyEvent`, ribbon state reflected from `LOK_CALLBACK_STATE_CHANGED`. The
Android `LOKitThread`/`LayerView` architecture is the closest published blueprint.

Not started, and not claimed anywhere until a booted screenshot shows a chart drawn this way.
