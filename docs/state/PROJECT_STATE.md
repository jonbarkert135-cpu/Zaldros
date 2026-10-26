# Project state — 2026-10-26

Current source baseline: `12afe1f572193fa105e0b2cd27a77b0715b4d605`.
P01 documentation changes are uncommitted. This page supersedes the old current-status
summary; it does not retrospectively reclassify historical test runs.

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
| Current implementation evidence | Local unit, mock-service bus, filesystem/PTY and offscreen checks; actual target-service/VM/hardware evidence is not refreshed here |
| Updates/recovery | Query/refresh implemented; complete update/install/recovery lifecycle not delivered; apt has no inherited bootc atomicity |
| Current work | P01 DONE; next P02: asset provenance and rootfs verification before extraction |

## Verification

P01 repeated tools: **44 passed**. Focused Settings/backend/files/KWin-wiring checks:
**112 passed, zero skips**, 72.69s. The preceding audit of the same source HEAD ran
shell/backend: **514 passed, 1 skipped** (Pillow missing), 61 forkpty warnings.
Office: Writer audit **9 passed / 6 skipped**; P01 Sheets **6 passed / 9 skipped**,
Slides **3 passed / 12 skipped**. Missing LibreOffice/UNO means no Office engine
readiness claim. Compatibility registry check: 8 app / 13 hardware entries accepted
by the evidence gate; this does not establish compatibility on real hardware.

No current-SHA ISO build/boot, real KWin session, installed-system test, or physical
hardware run was performed in this cycle. The current container lacks a confirmed
running systemd desktop and QEMU/KVM prerequisites. This is an environment limitation
for those checks, not evidence that every service adapter is broken.

## Confirmed issues and priorities

1. **P0 / P02:** rootfs fetch goes directly from curl to tar without checking an
   authenticated checksum manifest. Fix verification before a privileged build.
2. **P1 / P04:** synchronous GUI-to-service path and reconnect/subscription recovery
   need fault-injection evidence and an operation lifecycle.
3. **P1 / P05:** taskbar and internal window model do not prove external-window behavior.
4. **P1 / P16:** Settings fonts says Selawik while the shell preference is PT Sans.
   Sixteen toggle rows have no backend control; static status must not imply measurement.
5. **P1 / P03:** ISO path filters omit backend/apps/assets; Office jobs described in
   docs are absent from the active CI workflow.

See F01–F12 and D01/D02 in the capability register for scope and confidence.
No functional application code was changed by P01.

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
