# Iteration 0010 — P01: capability baseline

Date: 2026-10-26. Source HEAD: `12afe1f572193fa105e0b2cd27a77b0715b4d605`.
Outcome: uncommitted documentation changes; no push or publication.

**CURRENT TASK** — Start the owner's staged improvement plan. Execute P01:
identify actual implementation, connect user scenarios to backend/tests, reconcile
current status and define a developer-alpha acceptance boundary.

**DONE** — Added `docs/development/CAPABILITIES.md`: 35 scenario groups and an
exhaustive index of 69 Settings pages with source/control/test/evidence gaps.
Reviewed audit findings F01–F12 against unchanged source. Updated root README,
PROJECT_STATE, ROADMAP and handoff pointers. Preserved old state/roadmap byte-for-byte
in `docs/state/history/pre-P01/`; historical reports and ADRs remain unchanged.

**RESULT** — P01 DONE. The next implementation task is P02 trusted rootfs extraction
and component provenance. No claim that the OS/backend is fully working.

**PROBLEMS** — UNIT/mock-bus passes do not establish live-service readiness.
Current VM/hardware acceptance is missing. Confirmed D01: Settings displays Selawik
while shell font preference is PT Sans. Sixteen toggle rows have no control binding.
Rootfs archive currently streams from HTTPS curl directly to tar before checking an
authenticated checksum manifest (D02/F08). Office engine tests skip without UNO.

**FIX** — This stage corrects status/documentation, not application behavior.
Current and historical evidence now have separate labels; absent install/update/
recovery paths are not advertised. D01 is queued for the UI state/translation task;
D02 is the first code change in P02, before a privileged build. No bulk rewrite,
base change, new dependency or new ADR was justified by this inventory.

**TESTS** — P01 tools: 44 passed; targeted shell/backend/Settings/files/KWin-wiring:
112 passed, zero skips. Sheets: 6 passed/9 skipped; Slides: 3 passed/12 skipped,
missing engine/UNO. All pytest commands exit 0. Compatibility gate passes 8 app/13
hardware records from its documented cwd. An initial invocation from the repository
root failed with module-not-found; retry from tools/zaldros-compat succeeded without
code changes. Previous same-HEAD audit shell result 514 passed/1 skipped is explicitly
historical to P01, not a new full run. Exact commands and timing: PROGRESS.md.
Document consistency checks cover links, Settings IDs, scenarios, prompts, archive
preservation and whitespace. No ISO/system/E2E/hardware run occurred.

**METRICS** — No performance claims. Counts describe executed tests and inventory,
not percent completion. No packages installed during P01. Existing tests were
sufficient; no implementation-mirroring tests added for documentation changes.

**NEXT** — P02: authenticated manifest/signature/digest before rootfs extraction,
negative tamper tests and clear failure/fallback behavior. Inventory actual shipped
assets/dependencies and licenses/notices; do not mark P02 complete until both gates
are satisfied. P03 CI and P04 async/recovery follow in the agreed sequence.
