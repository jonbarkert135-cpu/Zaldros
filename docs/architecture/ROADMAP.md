# Zaldros OS — current development roadmap

Updated 2026-10-26 at source baseline `12afe1f572193fa105e0b2cd27a77b0715b4d605`.
The current target is **developer alpha**, not a release-ready OS. See the
[capability register](../development/CAPABILITIES.md) for code and test evidence.
The executable sequence is [P01–P20](../development/PLAN.md), with
[task prompts](../development/PROMPTS.md) and [progress](../development/PROGRESS.md).

## Active sequence

1. **P01 DONE:** inventory real capabilities, reconcile current status and define alpha scope.
2. **P02 NEXT:** clean-room provenance and authenticated rootfs verification before extraction.
3. **P03–P04:** reproducible development/CI, nonblocking operations and service recovery.
4. **P05–P16:** real KWin windows and complete Linux user workflows, including error paths,
   application/update lifecycle, authorization, RU/EN and accessibility.
5. **P17:** current-source integrated alpha ISO/VM gate and variant decision.
6. **P18:** installed-system workflow and tested recovery.
7. **P19–P20:** Office/Windows compatibility evidence, hardware/performance/security and release.

Only P01 is complete. Later items are work packages, not verified features.
A partial stage remains PARTIAL; an unavailable VM does not turn its gate into PASS.
Do not skip P02 verification to obtain a faster privileged ISO build.

## Mapping to specification phases

PART 5 section 15 defines phases 0–14. They remain requirement categories; Pxx task
numbers are a separate execution sequence. This replaces the old document's conflicting
0–14 table and second 0–5 numbering, without changing the specification.

| Spec phase | Current implementation evidence | Remaining gate / task sequence |
| --- | --- | --- |
| 0 Research/architecture | spec and ADRs exist; base/variant acceptance remains open | P01–P04, then measured variant decision in P17 |
| 1 Minimal bootable base | Ubuntu ISO/boot code; historical CI reports | trusted current-SHA image and verified boot, P02/P03/P17 |
| 2 Graphics/compositor/desktop | KWin session recipe, theme and tabbox/scripts | real surfaces, workarea, multi-monitor, P05/P10/P17 |
| 3 Shell | executable Qt/QML prototype and offscreen tests | full external-app interaction and recovery, P04/P05/P17 |
| 4 Taskbar/Start/Search | UI, installed-app search, launcher, internal window model | desktop-entry semantics and real window tracking, P05/P06 |
| 5 Explorer | real filesystem operations and local tests | copy/move/trash restore, long operations, MIME/E2E, P11 |
| 6 Settings | 69 pages, service-backed controls plus static/unimplemented rows | actual service readback, truthful status, safe writes, P07–P16 |
| 7 System utilities | PTY terminal, process/device/service adapters and tools | permissions, lifecycle and real-system scenarios, P11/P14/P17 |
| 8 Application management | installed list/default MIME; PackageKit query/refresh | install/remove/update/reboot/recovery, P15/P18 |
| 9 Windows compatibility | registry/evidence gate, not a tested universal runtime | selected Wine/Proton cases, P19 |
| 10 Installer/recovery | design contract, no completed installer/rollback | install on disposable disk and recovery, P18 |
| 11 Performance | benchmark harness and idle-activity guards | comparable current baselines, no UX loss, P17/P20 |
| 12 Hardware compatibility | inventory/registry; no refreshed hardware acceptance | explicit tested hardware matrix, P20 |
| 13 Security audit | design and polkit/permission adapters, not completed audit | provenance, authorization, threat review, P02/P13/P20 |
| 14 Release candidate | no release readiness claim | required functional/install/update/recovery/security gates, P20 |

## Acceptance rules

Correctness → stability → security → hardware compatibility → usability → performance
→ visual similarity → advanced features. No sacrifice of safety or function for RAM
or resemblance. U/B (unit/mock-bus) evidence does not imply real-service, E2E or hardware
PASS. A screenshot and a successful request are not completion of a state-changing action.

Every task records source SHA, environment, exact commands, exit codes, executed/skipped
checks and artifacts. Mandatory missing checks stay BLOCKED/UNRUN. Timelines will be
estimated after P04 and P17 from measured work, not invented now.

The [pre-P01 roadmap](../state/history/pre-P01/ROADMAP.md) preserves the earlier text.
Historical iteration reports and accepted ADRs were not rewritten by this status update.
