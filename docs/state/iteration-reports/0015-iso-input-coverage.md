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

**TESTS** — Initially 64 tools passed; after adding an explicit guard against
mistaking another event's filter for push: **65 passed**. Existing functional
acceptance tests: **48 passed**. Workflow copies and whitespace checked.

**REMOTE ACCEPTANCE** — Source `38ba1043251cc78912cdbb96539902e58c4b28f3`.
Normal CI `40459015507`: 8/8 jobs PASS. Native push ISO run `40458956429`:
3/3 builds, 9/9 boots PASS. All nine fresh raw reports rechecked through report.py:
exit 0, 99/99 required UI PASS, decoded 1280×800 screenshots, same-UUID geometry
change and minimize/restore transitions. Rootfs authentication confirms identical
archive SHA256 in all builds. Workflow metadata, pinned diagnostic commits and
observations: `../evidence/iso-input-coverage/vm-acceptance.json`.

**INPUT RECEIPT** — 99 recipe paths (32 previously uncovered), 159 inventory/
validation paths (all previously uncovered), 36 planned app inputs (all previously
uncovered); now zero missing in each group. Record and model hash:
`../evidence/iso-input-coverage/input-coverage.json`. The model deliberately covers
literal paths/directory-/**, not general YAML or arbitrary GitHub glob syntax.
The final guard/evidence follow-up does not change verified workflow/runtime files.

**BOUNDARIES** — No runtime/performance change or complete P03 claim. Office
frontends are not currently copied into the image by the recipe; apps coverage
does not deliver that packaging. P02 licensing, dev bootstrap, installed-system,
hardware and P04 asynchronous/recovery work remain open.

**NEXT** — Run CI for the final guard/evidence follow-up and merge normally.
Continue P03 dev bootstrap/reproducibility before the P04 operation lifecycle work.
