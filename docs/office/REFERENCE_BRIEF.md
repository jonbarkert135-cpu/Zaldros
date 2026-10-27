# Office reference brief — owner instruction, 2026-10-27

The owner supplied three screenshots of real Windows Office interfaces and asked
that Sheets, Writer and Slides follow those examples while retaining their current
engines. This brief preserves that instruction for subsequent development.

## Engine and implementation contract

- Sheets keeps LibreOffice Calc; Writer keeps LibreOffice Writer; Slides keeps
  LibreOffice Impress. Continue the existing integration and its real-engine tests.
- Build the Qt interface around the observed workflows. Formula evaluation,
  document structure, formatting and file formats continue to come from LibreOffice.
- Bind visible commands to working engine operations. Unsupported actions must
  have an honest unavailable state/reason rather than a decorative success.
- Preserve Zaldros application names, licensed project fonts/icons and RU/EN
  localization. Reference screenshots are research material; do not ship their
  logos, account information, document artwork or watermarks as application assets.

## What the supplied examples establish

| App | Observed reference structure | Development target |
| --- | --- | --- |
| Sheets | Green title area; dense tabbed ribbon with grouped commands; name box and formula bar; row/column headers, selected cell/table; sheet tabs, status and zoom | Familiar spreadsheet navigation and formatting connected to actual Calc cells/formulas |
| Writer | Blue title area; command tabs and Home groups for clipboard, font, paragraph, styles and editing; central page; status, view and zoom controls | Real document editing/formatting with an identifiable page area and engine-derived content |
| Slides | Orange title area; grouped ribbon; numbered slide thumbnails on the left; central slide; notes below; view/zoom/status controls | Selection and editing of actual Impress slides, shapes and notes |

The screenshots differ in styling, language and display scale. Exact Office
versions/DPI are not established. One Word image was resized in the conversation;
do not turn its displayed pixels into claimed original measurements.

## Required comparison before UI changes

1. Capture the current app from the same source revision and record the engine,
   viewport, display scale, locale and document fixture used.
2. Compare the app with its corresponding reference: group layout, density,
   hierarchy, work area and the behavior of selection/editing/formatting.
3. Separate measured values from inferred values. In particular,
   `system/theme/word-reference.json` currently derives ribbon geometry from an
   Excel reference; it is not a measured Word baseline. Replace that derivation
   only after recording an actual Word-specific measurement/source.
4. Use owned/licensed DOCX/XLSX/PPTX fixtures and inspect real round trips and UI
   interaction. A chrome render alone does not certify a working editor or full
   Microsoft Office compatibility.
5. Keep optional/no-engine render checks distinct from the required real-UNO
   engine/UI suites described in [BUILD.md](BUILD.md).

These screenshots are currently conversation references, not newly archived
files in the repository's reference library. This iteration records the UI target;
it does not claim that the supplied designs have already been implemented.
