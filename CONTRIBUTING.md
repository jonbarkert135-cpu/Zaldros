# Contributing to Bedrock Linux

## Non-negotiable rules (spec PART 1 §15, PART 5 §22)
1. A compile, a boot or a screenshot is **not** proof that a feature works. Attach a test.
2. Never claim compatibility without an evidence record — `tools/bedrock-compat` enforces this in CI.
3. Never hide a failure or silently delete failing functionality. Reproduce → logs → root cause →
   hypothesis → fix → rerun → regression test.
4. Performance changes require a baseline and a comparison from `tools/bedrock-bench`; a change with
   an unmeasured metric is INCONCLUSIVE, not ACCEPT.
5. Never overwrite known-good code without a commit or backup.

## Workflow
- Branch, commit with a description of the change, the tests run and any benchmark numbers.
- Run `python -m pytest tools -q` before pushing; CI runs the same plus the evidence gate.
- Every meaningful iteration gets a report in `docs/state/iteration-reports/` in the PART 1 §16 format.

## Code
- Python for tooling (stdlib only where possible), Qt6/QML for shell and system apps, Rust for new
  non-GUI daemons, C++ where Qt/KWin requires it.
- Third-party components must be added to `THIRD_PARTY_LICENSES.md` with project, version, source,
  license, modifications and redistribution requirements.

## License of new code
Undecided — see `docs/SPEC_AUDIT.md` B4 (recommendation: GPL-3.0-or-later). Do not add substantial
new code until this is settled.
