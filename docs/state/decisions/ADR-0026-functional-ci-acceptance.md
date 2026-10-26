# ADR-0026 — Functional results control the ISO gate

Date: 2026-10-26. Status: Accepted for implementation; new VM validation is recorded
in PROGRESS.md. Extends ADR-0021 without claiming that all release gates are complete.

## Problem and evidence

ISO run 40333303076 on 6168e9b produced BOOT PASS for all nine targets, yet the
guest screenshot step reported FAIL for all three legacy profiles. Every job was
green because report.py checked only the `boot` label. The minimal recipe did not
install either screenshot program attempted by the actual guest test.

Replaying the retained reports through the corrected gate returns 1 with exactly
those three screenshot failures; their original measurements stay unchanged.

## Acceptance contract

Boot checks and the following eleven UI checks are required for every variant:

| Producer | Required checks |
| --- | --- |
| Guest | desktop_ready, app_launch_explorer, window_move, minimize, restore, screenshot |
| Host / QMP | start_open, start_close, alt_tab, task_view, taskbar_response |

Each required check needs an exact PASS from its owner. Missing, skipped, blocked,
malformed or unknown results cannot satisfy it. Guest BLOCKED records for steps
measured by the host remain explanatory; they do not replace the host result.
A failure from either observer must not be discarded in favor of another PASS.
Explicit diagnostic/report-level failures and QMP errors also fail acceptance.

Unmeasured frame pacing remains BLOCKED and is not part of the VM acceptance set:
emulated rendering cannot certify physical GPU frame pacing. If a diagnostic is
actually measured and reports FAIL, it is still a failure. The final success line
states the limited boot/UI scope rather than implying hardware certification.

Producer and consumer share boot_checks. Failed units cannot be hidden by a
`degraded` label. `starting` is permitted only with a nonempty set of pending jobs
whose exact unit names are the self-test or graphical.target. Empty/missing job
evidence or an unrelated unit fails. Columns and exit status use the same verdict.
The boot driver exits nonzero when its boot facts fail or its marker is absent.

Both ISO workflow copies pass the expected variant/profile to report.py. A missing,
different, duplicate or extra target fails. This does not yet bind report contents
to an immutable source SHA/run ID inside the guest; that provenance gate remains
P17 work. A source label is not substituted for an unverified guest measurement.

## Fix the missing function rather than hiding it

Spectacle plus xdg-desktop-portal and its KDE backend are common BASE dependencies.
All three variants must support the screenshot function already required by the
guest test and exposed by the shell. They were previously installed only by full
and services. The existing Spectacle integration is reused; no new capture engine
or security bypass is introduced. ffmpeg recording remains a full-only extension
and is not added to this eleven-step gate.

This changes the minimal variant's package/resource baseline. Earlier ISO size/RAM
measurements remain historical; do not reuse them as measurements of this recipe
or claim a performance improvement. Rebuild/boot all variants before acceptance.

## Validation and boundaries

Regression tests cover a complete pair of reports, missing owners, all mandatory
steps, rejected statuses, conflicting observers, explicit failures, malformed JSON,
duplicate/stale targets, transient systemd state and actual CLI exit codes. The real
boot-script composition heredoc is exercised from outside the checkout, including
a failed boot and a failed screenshot. Runtime package checks protect every variant.
Actual ISO/VM runs remain necessary for the package fix and are tracked separately.

This fixes one P03/P17 acceptance defect. It does not close the remaining P02
licensing review, Office CI, async backend, installer, recovery or hardware work.
