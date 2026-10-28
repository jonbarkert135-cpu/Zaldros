# Iteration 0021 — P04 asynchronous update check

Date: 2026-10-28. Base main: `b86f4a95c49ae6676a2c41cf46a53d1199becb07`.

**TASK** — Continue the authorized PR-only development workflow; remove the GUI
stall for one real Settings action. Explain environment publication separately
from GitHub commits/PRs and release/ISO publication.

**REPRODUCTION** — Export the pinned base backend and run the update-check latency
harness with a private real dbus-daemon/slow PackageKit-shaped test service. With
a 250 ms deadline, synchronous waiting blocks the 5 ms heartbeat for 257.294 ms.
Baseline and candidate loaded module paths/hashes are recorded. This does not
measure a complete Settings session, real network update speed or VM frame pacing.

**CHANGE** — Settings update reads use an explicit not-checked/confirmed cache.
The check action starts one worker which creates, owns and closes its private Bus.
Refresh and GetUpdates share one absolute budget; reply waits support cooperative
cancellation. Queued completion preserves terminal/generation state, repeated
clicks cannot queue more workers, and timeout/cancel never claims zero updates.
Pin PackageKit calls and transaction signals to one unique owner, detect owner/
transport loss, and require Finished before publishing a count. Repaint update
rows from cache without rebuilding unrelated Settings pages. The QML stop button
says stop waiting: remote metadata refresh may still finish. No package installation.

**ALTERNATIVE / DECISION** — Bundled QtDBus native async stays responsive but its
automatic GetAll conversion still returns QDBusArgument in the tested binding.
Current worker is an incremental slice, not a general transport replacement.
FD support/limitations and installed license metadata are explicit in ADR-0027.
No new environment dependency or publication is required by this change.

**LOCAL CHECKS** — Final targeted suite: **18 passed**, no skips. Covers actual
QML mouse activation and Space cancellation, independent readback, successful
Finished, denial, hung/silent reply, owner loss, foreign Finished, total deadline,
worker ownership, no queue, late results, cached-only row updates, idle/no data,
invalid deadlines and thread-start failure. Final latency sample: **5.297 ms**;
compare with 257.294 ms only for the same injected-fault/heartbeat metric.
Final full shell/backend: **639 passed**, zero skips, 62 existing forkpty warnings,
148.65s; tools: **81 passed**, zero skips, 2.88s. The pinned-base deadline regression
fails as expected: two 80 ms phases incorrectly succeed under a 120 ms budget.
It passes with the shared deadline. Exact commands, failures and source hashes:
[local.json](../evidence/async-updates/local.json). Remote outcomes follow CI.

**REMOTE ACCEPTANCE** — Source `2056a7c72416340190e3a69602e7452a7046eadc`,
PR [#9](https://github.com/jonbarkert135-cpu/Zaldros/pull/9), CI
[40767182098](https://github.com/jonbarkert135-cpu/Zaldros/actions/runs/40767182098):
all eight jobs PASS. Real UNO: Writer 40, Sheets 15, Slides 15, zero failures/skips.
Actual PR checkout and source have identical Git tree
`db3585fdb6bba31d0e963db8d4b6438b4c0bf58b`.
[CI receipt](../evidence/async-updates/ci-acceptance.json) records jobs/Checks notices;
no uninspected remote shell pytest count is invented. This follow-up changes
documentation/evidence only. Final follow-up checks, ISO `40767127413` and merge
state are recorded on PR #9; this source receipt does not assert an unfinished
workflow passed. Transport setup/teardown can delay worker cleanup/retry after
the GUI deadline; 50 ms cancellation polling does not cover those control phases.

**FAILURES RETAINED** — Initial focused test used repeated QTest.qWait calls that
starved Python workers; the normal Qt event loop passed. Use a test QEventLoop
instead; production has no nested event loop. QML delegates require a visual-item
walk, and input requires an exposed window. Earlier full run: **637 passed /
1 failed**, 62 forkpty warnings, 147.32s; the failing QML test used the old lookup/
exposure helper. Final test retains real mouse/keyboard assertions. QML context
teardown also gets null guards. No failing assertion is removed to obtain green CI.

**LIMITS / NEXT** — P04 PARTIAL; unrelated Settings calls/initial tree construction,
bus transport recovery and broader operation migration remain open. Real system
PackageKit/polkit/network/installed-system/hardware checks are not established by
the private-bus service. General async transport selection and real Unix FD round
trip remain prerequisites for FD-dependent operations. Next: another measured
GUI read/action and transport recovery, preserving exclusive ownership and readback.
