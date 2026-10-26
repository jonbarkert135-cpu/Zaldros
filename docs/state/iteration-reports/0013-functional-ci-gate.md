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

**RESULT** — D03 fixed and VM-verified on source `4c35535`. ISO run `40375579596`
passed three builds and nine boot jobs; strict replay of their raw reports exits 0
with 99 required UI steps PASS. No historical failure was relabeled as passing.

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

**NEXT** — Merge PR after evidence documentation passes CI. Continue remaining
P02 licensing and P03 coverage before the P04 operation lifecycle work.
Source-SHA/run-ID binding within guest reports, licensing review, Office CI and
async backend remain subsequent work.

**FOLLOW-UP FINDING** — The first candidate dfe9237 still produced false PASS:
the guest step wrapper accepted an error dictionary as success. Raw services/
legacy reports contained PASS plus "no file" errors. That intermediate remote
success is not functional evidence. The final wrapper and consumer reject errors,
and the screenshot probe requires exit 0 plus a newly decoded image/dimensions.
kwin-common was missing in both minimal variants; its screenshot.so module was
confirmed through a signed Ubuntu metadata/hash chain and moved into BASE.
Window probes now track one Dolphin UUID and verify its actual state/geometry.

**FINAL LOCAL VALIDATION** — 612 passed, no skips, 62 existing forkpty warnings,
152.85s. Focused suites: 126 passed. The original capture wiring test was strengthened
to exercise failure through the real producer instead of matching an error string.
Replay now rejects six original screenshot failures including the in-band error
cases. A new remote run is required; earlier green jobs are not reused as proof.

**WAYLAND GEOMETRY FOLLOW-UP** — Run `40353950450` on `e5c98f0` correctly
failed all nine boot jobs on window_move. All nine screenshot probes now produced
decoded 1280×800 PNG files; minimize/restore and host steps passed. Exact report
commits and observations: `../evidence/functional-gate/geometry-failure.json`.
The Qt gadget reference generated three geometry setter calls, ending with the
old geometry before the asynchronous Wayland acknowledgement. A real QJSEngine/
QObject regression reproduces that behavior: old code fails, the detached single
rectangle request passes. KWin v6.6.6 scripting.cpp explicitly registers conversion
of plain objects with x/y/width/height. The acceptance assertion remains strict;
a new nine-VM run must confirm the geometry fix.
Local verification after this fix: 613 passed, zero skips, 62 existing forkpty
warnings, 152.23s; producer/gate 73 passed, tools 44 passed.

**REMOTE ACCEPTANCE** — Source `4c35535a33466c0b4c6bd28139e12b75c56f4a44`;
normal CI `40375589292`: five jobs PASS; ISO `40375579596`: three builds plus
nine boot jobs PASS. All raw reports were fetched and checked with report.py:
exit 0. Every target has 11 required UI PASS, a decoded 1280×800 screenshot,
and same-UUID move from (256,115) to (376,195), minimize and restore. Screenshot
sizes range from 307398 to 309895 bytes. Metadata, pinned report commits, package
versions and observations: `../evidence/functional-gate/vm-acceptance.json`.
Documentation-only follow-ups do not change this verified runtime source.
Guest/source binding, installed-system and hardware checks remain open.
