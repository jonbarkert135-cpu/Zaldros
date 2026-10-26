# Iteration 0014 — required real-engine Office CI

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

**METRICS / BOUNDARIES** — No performance, Office compatibility or installed-system
claim. Apt versions are recorded, not an immutable snapshot. P02 licensing and
remaining P03/P17 work remain open.

**NEXT** — Run the new matrix, inspect actual results/JUnit counts and repair any
real regression before merging. Then continue P03 coverage/bootstrap and P04's
measured synchronous-operation/recovery defects.
