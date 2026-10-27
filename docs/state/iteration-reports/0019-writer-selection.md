# Iteration 0019 — Writer selection formatting and mixed character runs

Date: 2026-10-27. Base main: `1ac61346e7372deb6a22509904d3d21e18925090`.

**TASK** — Continue P19: character formatting for selected text, keeping the
LibreOffice engine. Main integration remains explicitly authorized.

**PROBLEM** — The ribbon formatted entire paragraphs even when TextArea highlighted
only a few characters. Mixed engine formatting was preserved in files but not
painted by the plain-text paragraph preview. Range validation must not fall back to
whole-paragraph writes after a failed read or invalid Unicode boundary.

**CHANGE** — Read and write validated UNO character ranges using Qt UTF-16 selection
coordinates. Remember selection while focus moves to the ribbon; absent selection
retains whole-paragraph character formatting. Font controls wait for engine readback;
failed selection reads disable them and never fall back to formatting the paragraph.
Paragraph alignment/styles keep their existing scope, stated in the status bar.
Render basic engine text portions through QSyntaxHighlighter without replacing
editor text or undo history; unconfirmed draft text uses its base preview until
readback. Fields/non-text portions retain the explicitly limited preview.

Manual layout inspection also found TextArea width referencing its shadowing text
property rather than the page column: editor width was 421.28 vs parent 642 px.
Use parent width and test wrapping with a long paragraph; editor now stays 642 px.

**LOCAL** — Optional Writer **17 passed / 23 skipped** without matching UNO; tools
**81 passed**. Local checks cover highlighter text/undo preservation, failed range
read refusing writes and page-column wrapping. The archived image is an explicit
Qt test-double layout fixture, not a real UNO document screenshot. Code/image hashes
are in local.json. No new reference measurements or copied Microsoft assets.

New mandatory real-engine tests cover selected font/size/toggles, unchanged
neighbors, emoji/invalid bounds and DOCX/ODT persistence. Required Qt interaction
checks keyboard selection → ribbon → engine and painted ranges → Ctrl+S/reopen.
Remote acceptance is pending; local skips are not engine acceptance.

**LIMITS** — Selection within one top-level body paragraph only. No new formatting
for future typing at a collapsed caret; no-selection behavior is explicitly whole
paragraph. Cross-paragraph selection, complete field/object/page rendering,
multiline/rich paste, engine-wide undo and ISO frontend installation stay open.
Selection read/flush remains synchronous when its timer runs; P04 latency/recovery
has no new performance or completion claim.

**NEXT** — Required real-UNO CI, diagnose failures without weakening tests, record
source/results, then normal main integration. API GitHub still returns CONNECT 403;
use public CI pages for readback and ordinary Git merge/push if PR creation remains
unavailable. No admin bypass or invented PR number.

**INITIAL CI FAILURE / REPRODUCTION** — Source `c3dad87`, CI `40574578143`:
Writer **38 passed / 2 failed / zero skips** (engine 22 pass, UI 16 pass).
Both DOCX/ODT UI cases fail while inspecting painted QTextLayout formats through
a chained QQuickTextDocument/QTextDocument/QTextBlock expression: the temporary Qt
wrapper is released too early (`Internal C++ object ... QTextDocument already
deleted`). The separate Qt selection-input test-double probe reproduces it locally.
Keep named strong references through layout inspection; the probe then passes.
No engine, range, selection, painted-format or round-trip assertion is removed.
Original notices and HTML hash: `initial-ci-failure.json`. Remote rerun is required.

**FINAL REMOTE ACCEPTANCE** — Source `c625c8f93ac67969e943dd352c933da4e9f71b0f`,
CI `40575214293`: **all eight job types PASS**. Writer **40** (22 engine / 18 UI),
Sheets **15**, Slides **15** = **70 passed / zero failures/skips**, Python 3.12.3 /
LibreOffice 24.2.7.2. Both painted-run assertions and DOCX/ODT saves/reopens pass after
retaining Qt wrapper references. Previous failures remain separately archived.
Exact source/code hashes, public run/job HTML hashes and JSON notices are preserved
in `acceptance.json` / `final-source.json`. The archived image remains explicitly
a local test-double layout fixture, not a relabelled live-engine screenshot.

**STATUS / HANDOFF** — Selected-range/basic-run display slice verified; P19 PARTIAL.
Final follow-up records evidence only. PR creation still returns CONNECT 403, so
normal Git merge/push is the authorized fallback under server branch rules.
Next primary iteration returns to **P04 measured GUI/service responsiveness and
recovery**, using real fault injection and pinned baselines. Cross-paragraph
selection, richer rendering/paste/history and ISO frontend integration remain
open P19 work; no installed-system/hardware acceptance is added.
