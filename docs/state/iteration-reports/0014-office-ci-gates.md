# Iteration 0014 — real-engine Office CI and Writer readback fixes

Date: 2026-10-26. Base: `870c3610661507899cd0c5425629761062c54f3e`.

**CURRENT TASK** — Continue P03 by restoring real Writer/Sheets/Slides checks.
Owner authorization covers branch, push, PR and normal main merge.

**PROBLEM / REPRODUCTION** — Active CI has no Office job despite the Sheets build
documentation claiming one. With no UNO, ordinary Calc engine pytest reports
9 skipped and exits 0. The current container has a LibreOfficeDev executable,
but no UNO binding in either the shell venv or system Python; an executable alone
is not evidence that the Office bridge works. No local real-engine pass is claimed.

**FIX** — Three independent Ubuntu 24.04 jobs install the matching system Python,
UNO and app component. A system-site-packages venv holds pinned pytest/Qt without
writing system Python packages. The strict runner requires the dependencies,
executes both engine/UI suites and rejects any skip or missing suite. Writer's
missing-component test now injects that condition and runs even with Writer
installed. Normal CI contents permission is read-only. Stale CI reference/docs
are synchronized; no old unpublished container-retry behavior is activated.

**TESTS** — Tools: 53 passed (44 existing + 9 gate regressions). Real subprocess
pytest exercises passing, runtime-skip, collection-skip, empty, incomplete and
failed suites. Missing UNO/binary preflight paths fail. The actual new runner on
the local no-UNO interpreter exits 1 instead of accepting 9 skips. Remote Office
engine/UI validation is required before acceptance.

**REMOTE FINDING** — First source `03033fd`, run `40382270592`: Sheets and Slides
real-engine jobs pass; Writer's real test step fails. Artifact/log download from
this execution environment is rejected with HTTP 403. Added bounded Checks API
annotations for failures and executed-suite counts without increasing workflow
permissions or ignoring the failed result. Tools after this diagnostic addition:
55 passed; annotation escaping is covered. Fresh remote diagnosis is required.
The first annotation attempt was prefixed by pytest's unterminated progress line
and ignored by GitHub. A subprocess reproduced `F::error` / `100%]::notice`;
annotations now begin a new line and the regression includes preceding progress.

**WRITER ROOT CAUSES** — Run `40383136896`, source `376840d`, confirms 4 failures
out of 15 Writer tests with zero skips. Three fail because CharPosture is a UNO
FontSlant Enum, not an integer; the UI also reaches this broken readback. The
fourth confirms XText.getString() omits table cells. Read actual enum values and
write a typed UNO Enum; enumerate engine paragraphs/table cells for text. Keep
paragraph indexes consistent with style/format setters when a table intervenes.
Strengthen the existing ODT table round trip, and add real-engine italic-toggle
and post-table paragraph-selection regressions. Local Writer: 9 passed, 8 skipped
(no UNO); those skips are not acceptance. Remote Writer must now pass all 17.

**REMOTE ACCEPTANCE** — Source `50555cedb2cba41d70d0f1533e0ade1525eed92c`;
CI `40383962576` passes all eight jobs. Writer 17 (12 engine / 5 UI), Sheets 15
(9 engine / 6 UI), Slides 15 (11 engine / 4 UI): **47 passed / 0 skipped**.
Checks API runtime summaries confirm Python 3.12.3, LibreOffice 24.2.7.2 and the
system UNO module. Git tree equality confirms the PR merge checkout is identical
to the named source commit. All original real-engine assertions remain; the table
assertion is strengthened. Receipts: `../evidence/office-ci/acceptance.json`.
JUnit/version artifacts were uploaded, but downloads here return HTTP 403; test
counts and runtime were inspected via structured Checks annotations instead.
Subsequent documentation-only changes do not alter this tested implementation.

**METRICS / BOUNDARIES** — No performance, Office compatibility or installed-system
claim. Apt versions are recorded, not an immutable snapshot. P02 licensing and
remaining P03/P17 work remain open.

**NEXT** — Merge after the documentation/evidence follow-up passes CI. Then continue
P03 coverage/bootstrap and P04's measured synchronous-operation/recovery defects.
