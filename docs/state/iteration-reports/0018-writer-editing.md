# Iteration 0018 — inline Writer text editing

Date: 2026-10-27. Base main: `4514ba65742a8072731e1d8a5d808f25eb43aa35`.

**TASK** — Continue P19 after the Home ribbon: actual text entry and a usable save
path, retaining LibreOffice Writer. Push/normal main integration remain authorized.

**PROBLEM** — Paragraphs were read-only Text items. There was no caret, paragraph
split/join, visible Save action or unsaved-close protection. Rebuilding a QVariant
list after each readback would destroy editor delegates and their caret/selection.

**CHANGE** — Stable Qt paragraph-list rows and plain-text inline TextAreas. Coalesce
local drafts for 180 ms; explicit save/format/structural operations flush them first.
The engine changes only the common-prefix/suffix difference, preserving untouched
character runs. Validate actual cursor ranges before writes, including UTF-16/emoji
positions and UNO short-count limits. Enter splits at the caret; Backspace/Delete
join immediately adjacent body paragraphs only, refusing a table boundary.
Save/Save As and Ctrl+S/Ctrl+Shift+S use local DOCX/ODT paths and preserve the opened
path. Repeated save explicitly authorizes overwrite; PDF export keeps document path
and dirty state separate. Unsaved-close offers save/discard/cancel. Failed writes
or readbacks retain drafts, remain dirty and block successful save/structural edits.

**LOCAL** — Optional Writer: 14 passed / 18 skipped (matching UNO unavailable).
Tools: 81 passed. Qt input/caret/close tests use an explicit test double and do not
establish engine readiness. Initial QML load exposed an unsupported Backspace-specific
Keys handler (2 failed / 5 passed / 1 skipped); switched to generic key handling and
retained all checks. Real UNO tests cover mixed-format preservation, emoji/stale
input, table safety and DOCX/ODT round trips; UI covers input, Enter/Backspace,
caret survival and two Ctrl+S saves. Remote acceptance is pending.

**LIMITS** — Paragraph preview remains approximate, not engine page layout or mixed
run rendering. Ribbon formatting still targets a whole paragraph. Multiline paste
is retained as an uncommitted draft with an error; create paragraphs with Enter.
Cross-paragraph text selection, tables/images editing, engine-wide undo/redo, full
file lifecycle, rich text paste and ISO frontend integration stay open. UNO remains
synchronous during flush/readback; P04 responsiveness/recovery is not declared solved.

**NEXT** — Run mandatory real-UNO CI without skips, diagnose failures, record the
exact source/results, then normal main merge. GitHub API currently returns CONNECT
403; public run/job web pages and Git remain available. Prefer a PR if API recovers;
otherwise ordinary Git merge/push must respect server branch rules. No bypass.

**RENDER FOLLOW-UP** — The own no-engine render exposed a dialog implicit-width
binding loop and standard-shortcut ambiguity warnings. Give the unsaved dialog an
explicit width and bind all platform Save/Save As sequences; rerun rendering/tests.
GitHub API still rejects PR creation (CONNECT 403), while Git and public Actions
pages work. Do not claim a PR was created; retain the concrete body locally and
use normal Git integration after verified CI if the API remains unavailable.

**FINAL REMOTE ACCEPTANCE** — Initial `e7a88fc`, CI `40564986957`: all eight job
 types PASS, Writer 32 / zero skips. Final source `747cb015a8d78bba1bb917b7c1db8d287ab99d59`,
CI `40565144511`: **all eight job types PASS**. Writer **32** (19 engine / 13 UI),
Sheets **15**, Slides **15** = **62 passed / zero failures/skips** on Python 3.12.3 /
LibreOffice 24.2.7.2. Local optional checks remain 14 passed / 18 skips, separate
from real-UNO evidence. Source hashes, public run/job HTML hashes and exact JSON
notices are in `acceptance.json` / `final-source.json`.

The Qt test-double view was inspected locally with text/caret/Save control, explicitly
as layout evidence, not a live UNO screenshot. The archived image is the initial
no-engine render, with its own source hash. Native file-dialog interaction is not
claimed tested; the real engine UI test uses an existing local target for Ctrl+S.
ISO `40565144514` is in progress; recipe/runtime/frontend installation are unchanged.

**STATUS / NEXT** — Inline-edit/save slice verified, P19 PARTIAL. Final follow-up
records evidence only. API PR creation remains unavailable (CONNECT 403); no PR
number is invented. Perform an ordinary Git merge/push to main under server rules.
Next work remains cross-paragraph selection/range formatting, rich/multiline paste,
file lifecycle/undo and P04 measured GUI/service recovery; ISO frontend installation,
installed-system and hardware acceptance remain open.
