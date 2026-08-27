# ADR-0013 — Zaldros Sheets is our UI on LibreOffice's engine

**Status:** accepted, 2026-08-28. Follows ADR-0003 (Qt/QML toolkit) and ADR-0008 (own shell runtime).

## Context
Zaldros needs a spreadsheet that looks and behaves like modern Microsoft Excel. Two things are not
negotiable: we do not write a spreadsheet engine (formula evaluation, XLSX fidelity and chart
models are decades of work), and we do not ship stock LibreOffice Calc with a repaint, because its
window, menus and toolbars are visibly not Excel and not Zaldros.

Four routes were researched against primary sources (see `docs/sheets/ARCHITECTURE.md` for the
full evidence and links):

1. **LibreOfficeKit (LOK)** — the C ABI in `include/LibreOfficeKit/` implemented in
   `desktop/source/lib/init.cxx`: `paintTile` renders a document into a BGRA buffer,
   `postKeyEvent` / `postMouseEvent` feed input, `postUnoCommand(".uno:Bold")` drives commands and
   `LOK_CALLBACK_*` reports state. This is the seam Collabora Online and LibreOffice for Android
   use. It requires `#define LOK_USE_UNSTABLE_API`, and there is **no Qt or QML binding** — only a
   GTK widget (`lokdocview.cxx`) that is documented to crash when embedded in a Qt process.
2. **UNO / pyuno** — a stable, versioned API onto the live document model: cells, formulas,
   styles, ranges, charts, filters, `.uno:` dispatch. It has no rendering API at all; the
   LibreOffice developer blog says so plainly.
3. **Forking core** to replace only Calc's UI — `sc/` mixes UI and model, `sfx2/` owns the frame
   and dispatch for every LibreOffice application, and no "bring your own frontend" seam exists
   there. A full build is hours and tens of gigabytes, forever, on every rebase.
4. **VCL theming** — retints stock Calc. Cannot produce a ribbon. Excluded by the brief.

## Decision
1. **The engine is LibreOffice, always.** No cell value, formula result, number format or file
   read/write is computed by Zaldros code. If Calc cannot do it, Zaldros Sheets cannot do it, and
   we say so instead of faking it.
2. **The UI is ours, in Qt/QML**, built to measured Excel geometry the same way the shell is built
   to measured Windows 11 geometry — one reference screenshot per component, measured, diffed.
3. **Two channels to the engine, chosen per job:**
   * **UNO** for the document model — open, cell values and formulas, styles, sheets, save. This
     is the channel the first vertical slice uses, and it is the channel with an upstream
     compatibility promise.
   * **LOK** later, for pixel-faithful rendering of what only the engine can draw (charts, shapes,
     conditional formatting, print preview) into our own QML surface. We write that Qt tile view
     ourselves; nobody has published one.
3. **Out of process.** `soffice` runs as a headless child process and we talk to it over a local
   UNO socket. That keeps our licence obligations to redistribution of an unmodified package
   (`docs/sheets/LICENSING.md`), keeps an engine crash out of our address space, and lets the
   engine be updated by the distribution.
4. **No fork.** If we ever need a patch in core, it goes upstream or into a package patch, not a
   fork we have to carry.

## Consequences
* A first-run cost: the engine process must be started and its socket awaited. Measured in the
  sandbox on LibreOffice 7.4.7: `soffice` accepting UNO in about a second, a create → formula →
  save-XLSX → reload round trip completing immediately after.
* Features Calc lacks (Power Query, slicers, full VBA) are absent by construction. They are listed
  as absent in `docs/sheets/EXCEL_FEATURE_MATRIX.md` rather than promised.
* Our grid must stay a *view*. Any local caching of cell values is a cache, and the engine remains
  the single source of truth; a test asserts the round trip through the engine, not through the
  cache.
