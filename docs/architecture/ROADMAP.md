# Bedrock OS — Development roadmap

Phases follow the numbering fixed by spec PART 5 §15. A phase ends only when its acceptance criteria
are verified (spec PART 1 §15) — a build or a screenshot is never a gate.

| # | Phase | State |
|---|---|---|
| 0 | Research & architecture | in progress (see below) |
| 1 | Minimal bootable Linux base | blocked on a build host |
| 2 | Graphics + compositor + basic desktop | not started |
| 3 | Bedrock Shell | not started |
| 4 | Taskbar + Start + Search | not started |
| 5 | Explorer | not started |
| 6 | Settings | not started |
| 7 | System utilities | backends started (`bedrock-sysprobe`, `bedrock-hwinfo`) |
| 8 | Application management | not started |
| 9 | Windows compatibility | registry started (`bedrock-compat`) |
| 10 | Installer + recovery | not started |
| 11 | Performance optimization | harness started (`bedrock-bench`) |
| 12 | Hardware compatibility | matrix started, 0 evidence records |
| 13 | Security audit | not started |
| 14 | Release candidate | not started |

Priority order when phases conflict (PART 5 §16): correctness → stability → security → hardware
compatibility → usability → performance → visual similarity → advanced features.

## Phase 0 — Research & Architecture (current)
- [x] Base distribution comparison and decision (`docs/research/01`)
- [x] Desktop/compositor/toolkit comparison and decision (`docs/research/02`)
- [x] Layered architecture + technology stack (`docs/architecture/ARCHITECTURE.md`)
- [x] Roadmap, risk register, performance/security/testing strategies
- [x] First tool: `bedrock-sysprobe` (service & resource map generator, spec §7)
- [ ] Baseline measurement run inside a VM (boot time, idle RAM, service map) — needs a build host
- [x] Integrate spec PARTS 3, 4, 5 (all received)
- [x] Combined-spec audit: contradictions, gaps, risks (`docs/SPEC_AUDIT.md`)
- [x] Windows → Bedrock feature matrix (`docs/architecture/FEATURE_MATRIX.md`)
- [x] Benchmark harness `bedrock-bench` (PART 5 §1)
Gate: architecture documents reviewed + a reproducible baseline image builds in CI.

## Phase 1 — Bootable base image
- Containerfile for `bedrock-base` (core system, no shell) and `bedrock-desktop`
- CI: build image, boot in QEMU, run smoke tests, publish artefact
- Service/dependency map generated automatically from a booted VM
- Three performance profiles as systemd presets, each measured
Gate: VM boots to a Plasma/Wayland session, `bedrock-sysprobe` report attached to the build.

## Phase 2 — Bedrock Desktop Shell v1
Taskbar (pinned/running/previews/tray/clock), Bedrock Start, global search, quick settings,
notification centre, Run dialog, snap layouts, Alt+Tab, virtual desktops, multi-monitor.
Gate: PART 2 §25 acceptance tests — interaction, shortcut, multi-monitor, performance, visual regression.

## Phase 3 — Bedrock System Applications
Files (Explorer-like), Settings (Windows-11-organised), Task Manager, Terminal, Screenshot,
Store/Update UI, Recycle Bin, clipboard history.
Gate: every PART 2 §22 workflow completable without touching a terminal.

## Phase 4 — Compatibility, installer, hardware
Wine/Proton integration, Bedrock Setup installer, driver/firmware handling, hardware test matrix.

## Phase 5 — Release engineering
Signed images, update channels, rollback UX, telemetry-free diagnostics, documentation, ISO.
