# Project state — 2026-10-26

The current Office-CI cycle starts from main `870c3610661507899cd0c5425629761062c54f3e`.
Runtime-verified source: `4c35535a33466c0b4c6bd28139e12b75c56f4a44`.
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
| Current implementation evidence | Local tests plus source 4c35535 boot/UI validation: all three variants × three VM profiles; installed-system and hardware evidence remain open |
| Updates/recovery | Query/refresh implemented; complete update/install/recovery lifecycle not delivered; apt has no inherited bootc atomicity |
| Current work | P01 DONE; P02 PARTIAL: signature/hash gate, asset staging and live Ubuntu authentication verified; licensing reviews remain open |

## Verification

Current functional-gate change: **613 passed, no skips**, 62 existing forkpty
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
2. **P1 / P04:** synchronous GUI-to-service path and reconnect/subscription recovery
   need fault-injection evidence and an operation lifecycle.
3. **P1 / P05:** taskbar and internal window model do not prove external-window behavior.
4. **P1 / P16:** Settings fonts says Selawik while the shell preference is PT Sans.
   Sixteen toggle rows have no backend control; static status must not imply measurement.
5. **P1 / P03:** ISO path filters omit backend/apps/assets. Required Office CI is
   being added with real UNO/Qt and strict skip handling; remote confirmation is
   pending. The former documentation-only job claim has been corrected.
6. **P1 / P03/P17:** report.py previously gated only on `boot`, so a guest UI step
   could report FAIL while the workflow was green. **D03 fixed and VM-verified**
   on 4c35535: boot facts and eleven UI steps gate all nine targets. The missing
   screenshot runtime and geometry producer are corrected. Other P03/P17 work
   remains open. See ADR-0026 and iteration 0013.

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
