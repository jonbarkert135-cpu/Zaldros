# Iteration 0013 — functional ISO acceptance and screenshot runtime

Date: 2026-10-26. Base: `7660f2c3ec63dd592f88e6be8fb04d0fa58e5598`.

**CURRENT TASK** — Fix D03: a green boot job must not hide failed/missing mandatory
UI results. The owner authorized continuing this work, GitHub PRs and main merges.

**DONE** — Added explicit host/guest ownership of eleven required UI steps,
strict PASS acceptance, failure precedence and QMP/error propagation. Shared boot
facts between producer and consumer, corrected self-test pending-job handling and
driver exit status. Expected variant/profile is supplied by both workflow copies;
stale/duplicate/extra targets fail. Screenshot runtime is common to all variants.
Decision and scope: ADR-0026. Remaining P02/P03/P17 requirements stay open.

**RESULT** — Local gate behavior verified. New VM validation is required to accept
the legacy screenshot runtime fix; no historical report was relabeled as passing.

**PROBLEMS** — report.py only checked BOOT; legacy lacked Spectacle/portal packages.
The systemd table and producer used different acceptance rules; an empty pending
list could satisfy an all() condition. Missing/mismatched UI results were not gated.

**FIX** — Enforce the measured outcomes, reuse the same Linux screenshot backend
that already works in full/services, preserve nonzero command/pipeline exit codes.
Do not exempt the failing variant or disable assertions. The minimal package
baseline increases; no performance gain is claimed from old measurements.

**TESTS** — First new regression run on old code: 38 failed, 2 passed. Final focused
suites: 72 passed; full shell/backend: 587 passed, zero skipped, 62 existing forkpty
warnings, 154.20s. Tools: 44 passed. Replay of nine retained reports now exits 1 with
exactly the three known legacy screenshot failures. Actual boot-script composition
and command exit codes are tested. Shell syntax, workflow-copy consistency and
whitespace checks pass. Full commands/logs: PROGRESS.md.

**METRICS** — No UI/performance/hardware readiness claim. Every required UI step
is now an acceptance prerequisite; unmeasured frame pacing remains explicitly
outside VM certification. New ISO sizes/resource data need a new run.

**NEXT** — Publish PR, run ordinary CI and all three variants by three profiles,
inspect per-step results, diagnose any real failure and merge after verification.
Source-SHA/run-ID binding within guest reports, licensing review, Office CI and
async backend remain subsequent work.
