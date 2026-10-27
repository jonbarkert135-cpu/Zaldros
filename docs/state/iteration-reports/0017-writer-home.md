# Iteration 0017 — working Writer Home ribbon

Date: 2026-10-27. Base main: `c907842411cf80cae27f50ac99c9e8c5aea740b7`.

**CURRENT TASK** — Continue the owner's real Windows Office UI direction while
keeping LibreOffice Writer/Calc/Impress. P19 slice: Writer Home formatting.

**PROBLEM** — The old ribbon exposed clipboard/size/alignment labels with no action.
Bold/italic/underline always wrote true, so clicking again could not remove formatting.
The selected paragraph's engine formatting was not shown in the ribbon. The canvas
forced a guessed heading size/bold state instead of using engine values.

**FIX** — Grouped Home controls for Qt font family, 1–400 pt size (tenths),
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

**INITIAL REAL-UNO FAILURE** — Source `600043a`, PR run `40556254699`, Writer job
`122372995181`: 21 passed, 1 failed, zero skips (engine 14 / UI 7 passed). All mouse,
keyboard and readback assertions reached the screenshot step. The concluding
DOCX save/reopen path failed, but the long Unicode test-source annotation consumed
the available diagnostic budget before the actual exception. Full original Checks
payload is preserved in `initial-ci-failure.json`; it is not accepted as PASS.
Job-log download returned no log in this environment. Emit the actual pytest crash
message first, bounded in UTF-8 bytes, and use short terminal tracebacks. A real
pytest regression with a long Unicode source ensures the exception survives.
No document assertion has been removed; rerun is required to diagnose the cause.

**DIAGNOSIS / FIX CANDIDATE** — Improved diagnostics on `cecf3d4`, push run
`40556731365`, Writer job `122374662678`: the same 21 passed / 1 failed. Exact
assertion: reopened font `Liberation Serif` differs from selected generic Qt alias
`Monospace`. Preserve `diagnostic-ci-failure.json` and the unchanged equality check.
Resolve the selected Qt family through QFontInfo before submitting a concrete
family to UNO. Add DOCX alongside ODT to the concrete-font/fractional-size engine
round trip. Remote confirmation must establish whether this fixes the cause.
The actual engine receipt also shows the default style ID is `Standard`, so the
Normal card now uses that UNO ID and the real UI test checks Normal/Heading switching.

**CONCRETE-FONT RERUN** — `c5180ad`, PR run `40557228996`, Writer job
`122376422575`: 21 passed / 2 failed / zero skips. DOCX also loses concrete
`Liberation Sans`; resolving a generic alias is insufficient. Preserve
`concrete-font-ci-failure.json`. Remove that provisional alias mapping and target
an actual text cursor spanning paragraph start/end for character read/write,
instead of the paragraph's character defaults. Paragraph style/alignment still
use the paragraph object. Keep strict font equality and strengthen both ODT/DOCX
round trips to require bold/italic/underline ON after reopening too.

**FINAL ACCEPTANCE** — `babdfe8c287872b219b930eef0b72d0c7277b65a`, PR CI
`40557896014`: all eight job types PASS. Writer **23** (15 engine / 8 UI),
Sheets **15**, Slides **15**: **53 passed, zero failures/skips**, Python 3.12.3 /
LibreOffice 24.2.7.2. Real PR checkout `8138815510b460bcc08b3c49d2e227e638a0d22d`
has the identical tree `f6e30467c26be686b11fd6ea6a206a95b5eb4a35`. Both generic and
concrete-font assertions pass after targeting actual text ranges. The provisional
alias mapping was removed; it was not the cause. Bold/italic/underline ON persist
through ODT/DOCX and the UI checks on/off plus selection/style readback.

API access subsequently returned CONNECT 403; public GitHub run/job HTML remained
HTTP 200 and supplied final status and exact JSON annotations. Parsed acceptance,
HTML hashes and final code hashes are in `acceptance.json` / `final-source.json`.
Earlier failed runs and superseded cancellation metadata remain separate.
Writer artifact download is unavailable; its live PNG is not claimed inspected.
The inspected local no-engine image and temporary explicit test-double UI probe
are only layout/input evidence. No failed-run image is promoted to final acceptance.
ISO `40557888747` is still running; shipped recipe/runtime have not changed and
this does not install the Office frontend. Existing runtime evidence remains separate.

**STATUS / NEXT** — Writer Home formatting slice verified; P19 remains PARTIAL.
Final follow-up records evidence only. Normal merge to main is authorized; use
ordinary Git merge/push if the GitHub API remains unavailable, preserving server
branch rules. Next Office work is real text editing/selection and file lifecycle;
P04 service operation/recovery, P02 licensing and ISO frontend installation stay open.
