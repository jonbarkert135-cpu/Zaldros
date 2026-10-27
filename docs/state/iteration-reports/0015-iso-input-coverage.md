# Iteration 0015 — ISO push coverage of real inputs

Date: 2026-10-27. Base: `494a2775e6ecd6e9d9b426ec1dff938907063bfd`.

**CURRENT TASK** — Continue P03 after the four merged PRs. The owner also requested
a plain-language summary of those PRs; that summary was given in the conversation
and recorded in PROGRESS.md. Push/PR/normal main merge remain authorized.

**PROBLEM / REPRODUCTION** — ISO builds copy the backend, stage and validate assets,
read the provenance manifest and install the log helper, but their push filter
omitted those paths. App changes likewise did not schedule an ISO rerun. New
regressions against the old filter: 3 failed / 6 passed across actual recipe,
inventory and app input groups. Inputs are derived from the recipe and manifest
rather than duplicating a desired list of filter strings.

**FIX** — Select backend/apps/assets, build/provenance, all system configuration
and tools/collect-logs.sh alongside the existing recipe/shell/workflow inputs.
Keep docs and historical Fedora container changes outside heavy Ubuntu ISO CI.
Check literal-path/directory-/** selection and reference-copy consistency with
stdlib JSON parsing of the existing flow-list format. No new PR event or token
permission is introduced; this remains a repository-push/manual workflow.

**TESTS** — Tools: 64 passed. Existing functional acceptance tests: 48 passed.
Workflow copies and whitespace checked. Remote normal CI and all three ISO
variants × three VM profiles must be inspected before acceptance.

**BOUNDARIES** — No runtime/performance change or complete P03 claim. Office
frontends are not currently copied into the image by the recipe; apps coverage
does not deliver that packaging. P02 licensing, dev bootstrap, installed-system,
hardware and P04 asynchronous/recovery work remain open.

**NEXT** — Publish PR, inspect fresh normal/ISO results, diagnose any failure,
retain source/evidence and merge after verification.
