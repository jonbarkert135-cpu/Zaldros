# Iteration 0017 — working Writer Home ribbon

Date: 2026-10-27. Base main: `c907842411cf80cae27f50ac99c9e8c5aea740b7`.

**CURRENT TASK** — Continue the owner's real Windows Office UI direction while
keeping LibreOffice Writer/Calc/Impress. P19 slice: Writer Home formatting.

**PROBLEM** — The old ribbon exposed clipboard/size/alignment labels with no action.
Bold/italic/underline always wrote true, so clicking again could not remove formatting.
The selected paragraph's engine formatting was not shown in the ribbon. The canvas
forced a guessed heading size/bold state instead of using engine values.

**FIX** — Grouped Home controls for installed font family, 1–400 pt size (tenths),
on/off character formats, four paragraph alignments and four real Writer styles.
A model-owned paragraph selection supplies all control readbacks. Canvas uses the
engine's reported font/size/alignment and highlights the selected paragraph.
Formatting applies to the entire top-level paragraph; the UI says so explicitly.
No-document controls are disabled; unimplemented tabs say unavailable instead of
switching to the same ribbon. Removed inert commands and use our own window caption.
Mixed/unknown character values are not coerced to an invented positive state;
engine errors retain a reason and trigger a fresh readback. Validation refuses
invalid sizes/fonts/alignments before writing them. No engine replacement.

**TESTS** — Locally: optional Writer suite 11 passed / 11 skipped (no matching UNO),
tools 80 passed. Own 1280×800 no-engine render inspected; code/image hashes and
limits in `../evidence/writer-home/local.json`. An initial UI-test helper failed to
find Repeater delegates through QObject ancestry; fixed it to traverse the visual
tree and unload QML before releasing the model. No failed assertion was removed.

Added required real-UNO mouse/keyboard → QML → engine → reopened DOCX checks for
on/off formatting, font/size controls, selection readback, alignment and style.
Real-engine ODT coverage includes fractional size, post-table paragraph indexing,
invalid input preserving state and mixed character runs. UI test can archive its
owned-fixture screenshot/metadata in the existing Office artifact directory.
Remote confirmation is pending; local skips do not constitute engine acceptance.

**BOUNDARIES** — This is paragraph formatting, not a text-selection/caret editor,
faithful page-layout renderer or full Word compatibility. Ribbon overall heights
remain explicitly derived, not new Word measurements. Clipboard/file tabs, inline
editing, undo, table/image layout and installed-ISO frontend integration remain open.
Other Office apps and the backend operation/recovery P04 slice remain open.

**NEXT** — Run real UNO CI, diagnose any failures, inspect evidence, then normal
PR/main merge under repository rules. Preserve all failed/cancelled results.
