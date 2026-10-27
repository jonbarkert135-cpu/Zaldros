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

## Current own-app baseline

Captured from source `85cec38` using the fresh shell venv at 1280×800, offscreen,
without UNO or an open document: [Writer](../state/evidence/development-bootstrap/writer-chrome.png),
[Sheets](../state/evidence/development-bootstrap/sheets-chrome.png),
[Slides](../state/evidence/development-bootstrap/slides-chrome.png).
Hashes, commands and scope: [office-chrome.json](../state/evidence/development-bootstrap/office-chrome.json).

Observed gaps to address in P19:

- Sheets already has ribbon/formula/grid/sheet regions; compare grouping/density
  and verify selection/formatting against real Calc state with an open workbook.
- Writer's ribbon is mostly text commands. It needs engine-backed font/paragraph
  controls, style-gallery presentation and a Word-specific layout baseline.
- Slides has the thumbnail/canvas/notes regions but a minimal ribbon and limited
  content presentation. Expand from real Impress capabilities and document fixtures.
- Current reference-style window captions, mixed language and font labels need
  review against the own-branding/localization/document-state contract above.

These images verify that the chrome renders in the new environment. Their empty
or unavailable-document state is explicit; they do not demonstrate working Office
editing or parity with the owner's reference screenshots.

## Writer Home slice (iteration 0017)

The first implementation slice replaces the flat Writer commands with font/size,
character toggles, paragraph alignment and style-gallery controls. They target a
whole selected top-level paragraph, read back Writer state and disable without a
document. Clipboard and other unimplemented commands are not presented as working.
The source engine remains LibreOffice Writer. Iteration 0017 confirms 23 Writer
tests with real UNO, zero skips, including Qt input and DOCX/ODT persistence.
The local no-engine capture is not a document editing receipt.
This improves group structure/behavior; it is not a new measured Word geometry or
complete visual/functional parity claim.

## Selected text and mixed runs (iteration 0019)

Writer character controls now target the selection within one paragraph; without
selection they retain whole-paragraph behavior. Styles/alignment stay paragraph
operations, stated in the status bar. Basic engine font/size/character runs paint
inside the editor without replacing its text. Real-UNO acceptance is 40 Writer
tests without skips, including actual Qt selection/ribbon/painted-format checks
and DOCX/ODT persistence. The archived layout test-double image is separate from
that evidence. Complete page/field/object fidelity and cross-paragraph selection
remain open; no new measured Word geometry or full visual parity is claimed.
