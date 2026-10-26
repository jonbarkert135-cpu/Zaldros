# Iteration 0012 — canonical product branding and live evidence

Date: 2026-10-26. Base: main `6168e9bd5f55d879630d34b4e1ae0509ec1b3eb4`.

**CURRENT TASK** — Apply the owner's repository-wide naming cleanup, retain the
requested README contributor/funding section, and complete live verification
after GitHub/Ubuntu connectivity recovered.

**DONE** — Removed superseded product references from code, documentation,
research records and comments. Deleted obsolete third-party audit rows rather
than substituting false product names/URLs. Settings labels now use canonical
Zaldros OS with extractable gettext strings. Refreshed 44 tracked visual artifacts
from the renderer, keeping all reference measurements unchanged.

Retained official Ubuntu signed checksums, signature and extraction receipt.
The independently pinned fingerprint matches Ubuntu's official HTTPS tutorial.
Actual rootfs authentication/extraction passed. Main CI for 6168e9b completed
successfully; metadata is preserved alongside evidence. PR #1 is confirmed MERGED.

**RESULT** — Canonical branding is consistent in project files and current rendered
evidence. No Git history rewrite. This does not certify the OS as release-ready;
historical third-party license/source gaps and later functional gates remain open.

**PROBLEMS** — The old label also existed in screenshot pixels. Text replacement
alone was insufficient. Pillow was missing, so two visual tests had not run.
Artifact zip redirects use a further restricted blob host; Git evidence branches
remain available. Branch-protection metadata requires a scope not granted to this
integration; no rules were overridden.

**FIX** — Regenerate screenshots from corrected source, check source text plus OCR,
install Pillow/numpy in the development venv and pin their versions in the saved
environment install_script draft. Keep signed-archive verification separate from
VM boot/functional/hardware readiness.

**TESTS** — Full shell/backend: **538 passed, zero skipped**, 62 existing forkpty
warnings, exit 0, 146.71s. Settings/context-menu subset: 8 passed. Visual geometry:
110/110 checks. OCR: 38 tracked raster images scanned, zero superseded-label matches;
text search: zero matches. Earlier 536/1 results are retained as earlier runs,
not added to the final count. No reference target updated to force a visual pass.

**METRICS** — No performance claims. Funding stays a provisional US $5,300 target,
not a fabricated precise estimate. Owner-provided Bitcoin address checksum was
validated; no credentials/private keys were requested or published.

**NEXT** — Merge the reviewed changes through PR, retain final CI/ISO outcomes,
then continue unresolved provenance review and the staged development plan.

**REMOTE EVIDENCE UPDATE** — Source 6168e9b: all five normal CI jobs succeeded;
all three ISO builds and nine boot jobs succeeded. All nine published BOOT PASS
reports were inspected and exact report commit IDs retained. Guest screenshot
reports FAIL in every legacy profile while the workflow remains green: report.py
only gates on BOOT. This is D03, an open functional acceptance defect, not a full
UI pass. The current naming patch requires its own CI result after publication.
