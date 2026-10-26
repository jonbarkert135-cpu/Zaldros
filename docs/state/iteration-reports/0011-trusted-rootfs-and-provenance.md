# Iteration 0011 — P02: rootfs authentication and asset shipping inventory

Date: 2026-10-26. Parent: `ec1ca56`. Current commit contains this report.

**CURRENT TASK** — Continue P02, deliver changes to GitHub/main as explicitly
authorized by the owner, and adapt the requested contributor/funding README section.

**DONE** — Added an independent Ubuntu signer policy and a fail-closed rootfs
download/signature/digest/staged-extraction helper. Prevented failure diagnostics
from entering an unauthenticated rootfs. Added per-file provenance/shipping records,
hash-validated asset staging and exclusion of research references. Pinned cursor
source to a fetched full commit. Updated ISO dependencies, flat-layout regression,
build/license docs and README (including owner-provided Bitcoin mainnet address).

**RESULT** — Local implementation validated; P02 PARTIAL because real Ubuntu
endpoint validation and historical vendored-asset license reviews remain open.
No ISO, hardware or completed-OS claim is made. No release published.

**PROBLEMS** — GitHub API and Ubuntu endpoints are blocked with proxy 403 even
though native Git read/write works. The fallback icon archive has no exact license/
authors notice files; its per-file license ancestry is unresolved. First flat-layout
check failed because the harness only copied cp targets and omitted the new stage step.

**FIX** — Use real OpenPGP verification against a full pinned fingerprint; fail
before tar on any authentication error; no silent fallback. Update the harness to
run real staging, retain license notices and mark unresolved provenance honestly.
Saved narrow additional egress domains in the environment draft; do not misrepresent
that save as runtime application. Do not bypass GitHub branch rules or ask for a
new token merely because the API route is blocked.

**TESTS** — Final shell/backend suite: 536 passed / 1 skipped (PIL absent),
61 existing forkpty warnings, exit 0, 148.57s. Targeted authentication/provenance/
diagnostics/visual/flat-layout suites: 34 passed. Tools: 44 passed. Compatibility
gate: 8 app / 13 hardware entries pass. Both shell scripts syntax-check; helpers
compile; asset validation/staging and pinned upstream fetch succeed. Initial
targeted failure was corrected and rerun, not hidden. Exact commands: PROGRESS.md.

**METRICS** — 158 asset records, 154 shipped assets plus inventory, four excluded
research/generator files. No performance improvement claim. Real rootfs and VM
validation unavailable under current network/capability restrictions.

**NEXT** — Apply saved egress settings, validate Ubuntu's live signature/key and
manifest, resolve fallback theme license/source gaps or review a replacement.
P03 CI/dev reproducibility and P04 async service lifecycle follow when P02 gates
are satisfied. Main delivery uses ordinary Git merge/push if API remains blocked;
actual server acceptance and hashes must be verified separately.
