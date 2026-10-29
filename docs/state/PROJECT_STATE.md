# Project state — 2026-10-29

The P04 incoming-method routing cycle starts from main
`ea60e7323101d6647c16f13528e7f15c066efdf3` (PR #10 merged normally through GitHub).
Runtime-verified source: `85cec3877d44373b29f32efa13e6e18712ab50b8`.
Office engine/UI verified source: `c625c8f93ac67969e943dd352c933da4e9f71b0f`.
P01 and P02 deliveries are already committed and merged. This page supersedes the
old current-status summary; it does not retrospectively reclassify historical runs.

## Current milestone

**Developer alpha: integrate and verify real Linux workflows.** The project contains
more than UI: Python Linux-service adapters, Qt/QML shell, file operations, PTY terminal,
process/device inventory, LibreOffice bridges, and ISO/VM tooling. Completion of an
OS, installed system, or fully working backend is **not established**.

- [Capability register](../development/CAPABILITIES.md): 35 scenario groups, all 69
  Settings pages, code/test links, implementation gaps, evidence levels.
- [Plan](../development/PLAN.md) and [task prompts](../development/PROMPTS.md): P01–P20.
- [Session handoff](../development/PROGRESS.md): results and next concrete action.

| Field | Current evidence and decision |
| --- | --- |
| Product | Zaldros OS; naming authority: ../NAMING.md / ADR-0006 |
| Specification | All five parts in spec/; phases 0–14 remain specification categories, not sequential completion claims |
| Base | Ubuntu 26.04 live ISO is the active implementation candidate; ADR-0009 remains PROPOSED until accepted by its gate |
| Desktop | KWin 6/Wayland + own Qt/QML shell; internal QML windows and real compositor windows must be verified separately |
| Variant | full/services/legacy comparison still open; full is the first smoke-test control, not an accepted winner |
| Current implementation evidence | Local tests plus source 85cec38 boot/UI validation: all three variants × three VM profiles; installed-system and hardware evidence remain open |
| Updates/recovery | Query/refresh implemented; complete update/install/recovery lifecycle not delivered; apt has no inherited bootc atomicity |
| Current work | P01 DONE; P02 PARTIAL: signature/hash gate, asset staging and live Ubuntu authentication verified; licensing reviews remain open |

## Verification

The observed server-side incoming-method loss is addressed by retaining methods
alongside signals and sharing dispatch with ObjectServer.process. Outgoing RPCs
do not execute service callbacks reentrantly; client-only dispatch defers them.
FIFO survives callback failure, signals reach subscribers while the server runs,
NO_REPLY_EXPECTED is preserved, and closing a connection inside a handler is a
normal transport error. The activation child no longer needs its no-reply name
acquisition workaround. Frozen-base regressions: 10 FAIL / 1 PASS. Final focused
36 PASS, full shell/backend 657 PASS (62 existing warnings), tools 81 PASS, zero
skips/failures: iteration 0023 and evidence/incoming-method-routing/local.json.
Remote acceptance and merge will be recorded on the corresponding actual PR.
No notification-shell integration or automatic Qt drain scheduling is established;
owners still need to call process after RPCs even when the socket is no longer
readable. Real services, reconnect, remaining GUI reads and FD support remain open.
PR #10's final CI/ISO/replay passed (3 builds/9 boots, 99 required UI PASS), and
its actual PR body records the pinned receipts. Earlier pending notes are checkpoints.

P04 activation slice: well-known CreateTransaction activates an installed service;
method reply sender metadata pins the creator, with ownership verified after the
loss subscription. A replacement owner cannot silently complete the old operation.
Pinned base reproduces 5 failures/2 passes; final focused 35 PASS, full shell 646
PASS and tools 81 PASS, zero skips. Real private daemon/service-file child tests
are not real PackageKit/systemd integration. New observed generic server-side
METHOD_CALL parking/routing gap remains open. See iteration 0022 and its receipts.
Source `a053e14`, PR #10 CI `40772567142`: all eight jobs PASS, real UNO Office
40/15/15 with zero failures/skips. Follow-up/ISO/merge outcomes are recorded on
PR #10; source receipts remain pinned to the implementation they actually tested.
PR #9 final CI/ISO/replay passed; its PR body records 3 builds/9 boots and 99 UI PASS.

P04 next vertical slice: Settings update check runs on one worker with its own bus,
one deadline, stop-waiting semantics and confirmed readback. Cached update rows
avoid synchronous rereads when a result arrives. Local targeted: 18 PASS; measured
private-bus fault case: 257.294 → 5.297 ms maximum Qt heartbeat gap. QtDBus comparison
and FD/license limits: ADR-0027; [iteration 0021](iteration-reports/0021-async-update-check.md).
This does not complete P04 or establish real PackageKit/hardware acceptance.
Source `2056a7c`, PR #9 CI `40767182098`: all eight jobs PASS, real Office 40/15/15
without skips; local full shell 639 PASS and tools 81 PASS. Pinned receipts are in
evidence/async-updates/. PR #9 records final follow-up/ISO checks and merge state.
Worker transport setup/teardown retains finite control timeouts, so cleanup/retry
may lag the GUI's terminal deadline/cancel state.
PR #8 final ISO results are in its PR body: 3 builds/9 boots and 99 strict UI PASS;
pending notes below refer to the earlier evidence checkpoint. Its follow-up CI passed.

P04 first slice: well-known subscriptions follow daemon-authenticated owner changes
on the same bus, absent/unique senders are strictly filtered, presence caches follow
dispatched owner changes, and duplicate match rules have balanced cancellation.
Real private-bus fault tests include repeated service restart and facade/Qt event
delivery. System-service/hardware verification and bus transport reconnection remain
open; synchronous GUI calls and the async transport decision remain the next P04 slice.
Local full shell 620 pass / zero skips (seven new cases collected), final targeted
8 pass / zero skips, tools 81 pass. PR #8 CI `40756838384` on `1bb28ca`: all eight
jobs succeed; real Office remains 40/15/15 with zero failures/skips. ISO and final
documentation follow-up checks are separate pending runs.
Exact local/CI outcomes: [iteration 0020](iteration-reports/0020-service-owner-recovery.md).
GitHub API access is restored after environment publication. Delivery must use actual
PRs and normal GitHub merges; earlier historical direct-main fallback instructions
are superseded by the owner's correction.

Selection-formatting follow-up: local optional Writer **17 passed / 23 skipped**
(no matching UNO); tools **81 passed**. Character commands target a selection within
one paragraph, and Qt paints basic mixed runs reported by Writer. Long-text wrapping
is corrected with a regression. Source `c625c8f`, CI `40575214293`: **all eight job
types PASS**; Writer **40**, Sheets **15**, Slides **15**, zero failures/skips on
real UNO. Tests retain selection during ribbon use, inspect painted ranges and
reopen DOCX/ODT with unchanged neighbors. Iteration 0019 and
[acceptance](evidence/writer-selection/acceptance.json) record scope and limits.
Next primary iteration returns to P04 measured GUI/service responsiveness and
recovery; remaining P19 features stay open. Earlier accepted stages follow.

Writer editing follow-up: local optional suite **14 passed / 18 skipped** because
this interpreter lacks UNO; tools **81 passed**. Stable inline editors, guarded
draft flushing, paragraph split/join and local save/unsaved-close UI are implemented.
Source `747cb01`, CI `40565144511`: **all eight job types PASS**, Writer **32**,
Sheets **15**, Slides **15**, zero failures/skips on real LibreOffice/UNO. Tests
include unchanged mixed-run preservation, Unicode/table boundaries, actual Qt text
input/caret and two Ctrl+S saves/reopen for DOCX/ODT. Limits and exact scope:
iteration 0018 and [acceptance](evidence/writer-editing/acceptance.json).

Writer Home (P19 partial): grouped font/size, character toggles, alignment and
style controls now target a selected whole paragraph through the existing UNO
engine. Final local optional Writer: 11 passed / 12 skipped (UNO unavailable);
tools: **81 passed**. Real-UNO CI `40557896014` passes all eight jobs on source
`babdfe8`: Writer **23**, Sheets **15**, Slides **15**, zero failures/skips.
Character read/write now targets the actual paragraph text range; DOCX/ODT
persistence regressions caught and fixed the previous paragraph-defaults bug.
This is not an inline editor or full document-layout renderer. See iteration 0017,
[initial local receipt](evidence/writer-home/local.json) and
[final acceptance](evidence/writer-home/acceptance.json).

Development bootstrap: direct pins shared by tools/shell/Office and the same
preparation script used locally/CI. Actual fresh local venvs: **78 tools passed**,
**613 shell passed / zero skips**, 62 existing forkpty warnings, 148.98s. Read-only
inspection preserves venv file sizes/mtimes; repeated setup succeeds. Actual default
Office interpreter lacks UNO and fails before target creation. Remote bootstrap/UNO
confirmation is recorded for initial source 85cec38: eight CI jobs and all 47
Office tests pass. The final pip-destination isolation fix on d25e310 has **80 local
tools tests**, actual hostile-config verification, and all eight CI job types
passing across two runs of identical Git trees. The final runs each contain a
cancelled duplicate Office setup; neither whole workflow is called successful.
The selected real-UNO suites pass all **47 tests without skips**.
Receipts: [local setup](evidence/development-bootstrap/local-setup.json),
[initial CI](evidence/development-bootstrap/ci-acceptance.json),
[final CI and cancelled-job outcomes](evidence/development-bootstrap/ci-acceptance-final.json),
[destination isolation](evidence/development-bootstrap/destination-isolation.json).
The Office UI instruction preserves Calc/Writer/Impress engines; its screenshot
reference brief is linked in P19. The bootstrap itself did not refresh the UI;
the subsequent Writer Home slice is verified separately above.

ISO input-coverage cycle: tools **65 passed** locally after adding a push-event
guard; existing functional gate **48 passed**. Source `38ba104`: normal CI run
`40459015507` passes all eight jobs; ISO run `40458956429` passes three builds and
nine boot jobs. Strict replay of all nine fresh reports exits 0: **99 required UI
PASS**, decoded 1280×800 images and same-window move/minimize/restore transitions.
Rootfs authentication succeeds on the identical archive in all three builds.
Exact source/diagnostic commits and input counts:
[ISO coverage evidence](evidence/iso-input-coverage/vm-acceptance.json) and
[filter coverage](evidence/iso-input-coverage/input-coverage.json).
Final follow-up changes documentation and an unshipped guard regression, not the
verified ISO recipe/runtime. Guest/source binding and other evidence limits remain
explicitly recorded. Earlier cycle results follow.

Office cycle: tools **55 passed** locally. Real LibreOffice/UNO + Qt CI run
[40383962576](https://github.com/jonbarkert135-cpu/Zaldros/actions/runs/40383962576)
passes all eight jobs: Writer **17**, Sheets **15**, Slides **15** tests, zero
failures/skips. Python 3.12.3 and LibreOffice 24.2.7.2; UNO comes from the system
Python packages. The tested PR merge checkout has the identical Git tree to source
`50555ce`. Initial Writer crashes on FontSlant Enum and omitted table text are
fixed; real italic-toggle/table/post-table-formatting regressions pass. Exact
metadata and structured Checks receipts: [Office acceptance](evidence/office-ci/acceptance.json).
This is engine/offscreen-UI evidence, not full Office compatibility or installed
ISO integration. The following counts describe the earlier boot/UI change.

Earlier functional-gate implementation: **613 passed, no skips**, 62 existing forkpty
warnings, exit 0, 152.23s. Focused gate/producer/report checks before the geometry
regression: **126 passed**; producer/gate including that regression: **73 passed**;
tools: **44 passed**. Replaying the nine archived reports now returns exit 1 for
six legacy/services screenshot failures, including errors mislabeled PASS.
The guest producer, window readbacks and missing kwin-common runtime plugin are
also corrected. Run `40353950450` confirms decoded screenshots in all nine VMs,
but correctly fails all nine window_move checks. A Qt gadget/Wayland geometry
request bug was then reproduced and fixed; the rerun below confirms that fix.

**Accepted remote rerun:** [ISO run 40375579596](https://github.com/jonbarkert135-cpu/Zaldros/actions/runs/40375579596)
on `4c35535` passed all three builds and nine boot jobs. Rechecking all nine raw
reports with the strict CLI returns exit 0: 99 required UI steps PASS, decoded
1280×800 screenshots without errors, and the same Dolphin UUID moves from
(256,115) to (376,195), minimizes and restores. Normal CI run `40375589292`
also passed all five jobs. Exact workflow metadata, diagnostic commits and
observations: [vm-acceptance.json](evidence/functional-gate/vm-acceptance.json).
Guest/source SHA binding remains a stated evidence limitation. These results
certify the eleven-step boot/UI scope, not a complete backend, installed OS,
physical hardware or frame pacing.

After canonical-branding cleanup and installation of the missing visual-test
dependencies: **538 passed, no skips**, 62 forkpty warnings, exit 0, 146.71s.
Visual geometry: **110/110** checks; refreshed current renders. Text search and
OCR of 38 tracked raster images found no superseded product label.
The following P02 counts are the preceding runs, not additional tests to sum.

P02 final local suite: **536 passed, 1 skipped**, 61 existing forkpty warnings,
exit 0, 148.57s. Authentication/provenance/diagnostics/packaging subset: **34 passed**.
Tools remain **44 passed**. OpenPGP tests use real disposable signatures, not mock
verification. Asset staging and exact cursor-commit retrieval were exercised.

P01 repeated tools: **44 passed**. Focused Settings/backend/files/KWin-wiring checks:
**112 passed, zero skips**, 72.69s. The preceding audit of the same source HEAD ran
shell/backend: **514 passed, 1 skipped** (Pillow missing), 61 forkpty warnings.
Office: Writer audit **9 passed / 6 skipped**; P01 Sheets **6 passed / 9 skipped**,
Slides **3 passed / 12 skipped**. Missing LibreOffice/UNO means no Office engine
readiness claim. Compatibility registry check: 8 app / 13 hardware entries accepted
by the evidence gate; this does not establish compatibility on real hardware.

P01 did not run ISO/VM validation. Subsequently GitHub Actions run `40333303076`
on `6168e9b` completed all three ISO builds and nine boot jobs successfully.
The exact CI metadata and published-report commits are retained under
`evidence/p02-rootfs/`. Host UI steps and guest window operations have separate
statuses; the legacy guest screenshot step is FAIL in all three profiles, and
frame stability remains BLOCKED. Green job status is not full alpha acceptance.
The later branding patch is locally verified separately; the installed-system
and physical-hardware gates remain unrun. The local container itself still has no
confirmed running systemd/KWin desktop or QEMU/KVM workflow.

## Confirmed issues and priorities

1. **P0 / P02:** rootfs fetch now authenticates the checksum manifest and archive
   before extraction, with tamper tests. The live Ubuntu endpoint/signing-key check
   subsequently passed; evidence is in evidence/p02-rootfs/. Fallback icon provenance
   is unresolved.
2. **P1 / P04:** synchronous GUI-to-service path and bus transport reconnect still
   need an operation lifecycle and fault-injection evidence. Same-bus service-owner
   subscription recovery is addressed in iteration 0020, within its stated test scope.
3. **P1 / P05:** taskbar and internal window model do not prove external-window behavior.
4. **P1 / P16:** Settings fonts says Selawik while the shell preference is PT Sans.
   Sixteen toggle rows have no backend control; static status must not imply measurement.
5. **P1 / P03:** ISO push coverage now includes backend/apps/assets, provenance,
   system configuration and the shipped log helper. Input-derived regressions:
   tools 65 passed; source 38ba104 passes all nine VM targets. Office CI remains
   verified at 47 tests without skips on d25e310. The shared rootless dev bootstrap
   and destination hardening are locally and remotely verified in iteration 0016.
   Complete transitive/apt locking and other P03 reproducibility work stay open.
6. **P1 / P03/P17:** report.py previously gated only on `boot`, so a guest UI step
   could report FAIL while the workflow was green. **D03 fixed and VM-verified**
   on 4c35535: boot facts and eleven UI steps gate all nine targets. The missing
   screenshot runtime and geometry producer are corrected. Other P03/P17 work
   remains open. See ADR-0026 and iteration 0013.

7. **P19 / integration:** the ISO recipe does not yet install our Office frontends.
   Their real-engine/offscreen tests and apps path coverage do not establish
   installed-ISO integration.

See F01–F12 and D01/D02 in the capability register for scope and confidence.
No functional application code was changed by P01. P02 changes build authentication,
asset staging and source pinning; see the next iteration report and progress log.

## Historical evidence — preserved, not revalidated

The [previous state document](history/pre-P01/PROJECT_STATE.md) is preserved byte for
byte, including earlier contradictory “not built” and “boot PASS” claims. It is an
archive, not current status. The [previous roadmap](history/pre-P01/ROADMAP.md) is
also retained. Historical iteration reports and ADRs remain unchanged.

BUILD.md reports ISO workflow 33157358995 (2026-08-28, b85017e) with green build/boot
jobs. Other reports describe earlier failures and fixes, including switcher issues.
Those remote artifacts were not downloaded or independently checked in this cycle;
no historical PASS is silently promoted to a current-SHA acceptance.

## Remaining external decisions

Reference hardware for Wi-Fi/Bluetooth/GPU/suspend evidence; appropriate VM host;
Secure Boot/release signing policy; brand trademark clearance before release.
Name, license, default languages and opt-in encryption already have owner decisions
(ADR-0005/0006); do not ask those resolved questions again.
