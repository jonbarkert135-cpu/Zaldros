# Iteration 0016 — shared development bootstrap

Date: 2026-10-27. Base: `4a2612ccc426873223f502b2fed60c5be8c600ef`.

**CURRENT TASK** — Continue P03's reusable dev setup. The owner also supplied real
Office UI references and explicitly retained the current engines. That instruction
is preserved in REFERENCE_BRIEF.md and the P19 prompt; runtime UI/engines are unchanged.
Push/PR/normal main merge remain authorized.

**PROBLEM** — Dependencies were repeated across CI shell/Office setup, tools used
unpinned pytest, and no reusable local preparation command existed. The shell README
still claimed 32 tests and described old limitations. UNO requires the matching
system interpreter; a generic private Python cannot stand in for it.

**FIX** — One stdlib venv helper with tools/shell/office profiles, exact direct pins
in shared constraints, real import/version checks, and a read-only doctor mode.
Office uses the system interpreter and system-site packages; other profiles remain
isolated. Refuse non-venv/symlink targets, global/base-prefix aliases, mismatched
interpreters/site mode and incorrect dependency versions. Bind pip to the validated
venv and require a virtualenv; never invoke apt or global pip from bootstrap.
CI uses the same preparation command and exposes actual environment metadata.

**LOCAL TESTS** — Actual fresh tools/shell venv preparation succeeds. Tools:
78 passed; shell: 613 passed / 0 skipped, 62 existing forkpty warnings, 148.98s.
Tools setup repeated successfully; --check preserved real venv file sizes/mtimes.
Missing UNO on the actual default system interpreter returns 1 before target creation.
Safety regressions cover missing/invalid targets and dependencies, symlinks, wrong
site/base interpreter, version mismatch and pip isolation. Receipts and code/pin
hashes: `../evidence/development-bootstrap/local-setup.json`.

**BOUNDARIES** — Direct pins are not a complete transitive/apt lock. This prepares
development dependencies, not system services or an installed OS. Local UNO is absent;
real Office readiness must come from remote engine/UI tests. Owner screenshots remain
conversation references; no fabricated pixel measurement or UI implementation is claimed.

**INITIAL REMOTE ACCEPTANCE** — Source `85cec38`, CI `40467806652`: all eight
jobs PASS. Live environment annotations confirm shared setup in all three profiles;
Python 3.12.15 for tools/shell and 3.12.3/system UNO for Office. Writer/Sheets/Slides:
47 passed / 0 skipped on LibreOffice 24.2.7.2. ISO `40467806594`: three builds,
nine boots and strict replay of 99 required UI checks PASS. Receipts are preserved
as `ci-acceptance.json` and `iso-acceptance.json` in this iteration's evidence directory.

**DESTINATION FIX** — Review exposed ambient PIP_TARGET/config redirects despite
the venv interpreter guard. Regression on the previous child environment: 1 failed,
1 passed. Ignore destination/extra-requirement overrides and pip config files in
children; preserve explicit source/TLS/hash-policy environment settings. Disable
ambient PYTHONPATH/PYTHONHOME in children. Actual fresh tools setup under conflicting
target/prefix/user/log/config/module overrides writes only the requested venv.
Final local tools: 80 passed; current target imports/read-only checks pass. The
earlier fresh-shell receipt is retained with its original code hash. A fresh remote
run is required for this refinement. Actual receipts: destination-isolation.json
and local-final-checks.json; UI/engine/recipe sources remain unchanged.

**NEXT** — Publish PR, verify all three profiles in normal CI and required real-UNO
suites, inspect any ISO triggered by the shell README update, and merge normally.
Then proceed to the measured P04 operation/recovery slice; P02 licensing and remaining
reproducibility/permission hardening stay open.
