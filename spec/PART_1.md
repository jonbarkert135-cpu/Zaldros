# Bedrock OS — MASTER SPECIFICATION — PART 1/5 — VISION, RULES & ARCHITECTURE
Repo: https://github.com/jonbarkert135-cpu/bedrock_os
Received from Linussi Fril (Slack DM), 2026-08-23. Project name in spec: RAVEN OS.

Role: autonomous senior Linux systems architect / OS, DE, UI/UX, performance, security, QA engineer and researcher.
Goal: Windows 11-like desktop UX on a genuine, lightweight, highly optimised Linux OS.

1. CORE VISION — not copying Microsoft code; Windows-like UX/workflows/functionality + Linux architecture + aggressive optimisation. A Windows 11 user must be instantly at home.
2. LEGAL BOUNDARIES — no proprietary Windows source/components/binaries, no pirated ISOs, no license bypass, no protected MS assets without license check. Allowed: study public behaviour/docs, screenshots/videos as UX reference, independent reimplementation, open-source projects, forks per license, original implementations.
3. AUTONOMY — independently decide: distro base, kernel strategy, init, desktop architecture, compositor, display protocol, GUI toolkit, languages, filesystem, package manager, app format, updates, installer, HAL, security, Windows compat layer, performance architecture. Justify deviations with evidence.
4. LINUX BASE SELECTION — no default choice. Compare at minimum Debian, Arch, Fedora, Ubuntu + other modern bases on: stability, packages, hardware/driver support, kernel freshness, performance, boot time, maintenance, security, docs, community, customization, buildability, sustainability, suitability.
5. ARCHITECTURE — Kernel → Core System → Hardware/System Services → Display/Compositor → Raven Desktop Shell → Raven System Apps → User Apps. Core independent of visual layer; every daemon documented.
6. PERFORMANCE-FIRST — minimal resource use while stable/secure/functional. Loop: BASELINE → CHANGE → MEASURE → COMPARE → ACCEPT OR REVERT. Never remove components without understanding purpose/deps/consequences.
7. SYSTEM MINIMALISM — for each background service answer 9 questions (what, required?, dependents, RAM, CPU, boot impact, disableable?, security impact, hardware impact). Produce a service/dependency map.
8. PERFORMANCE PROFILES — Raven Desktop (everyday), Raven Performance (max responsiveness), Raven Legacy (low-end hardware). Each documented.
9. RESEARCH-FIRST — RESEARCH → ARCHITECTURE → SPECIFICATION → PROTOTYPE → TEST → IMPLEMENTATION. Preference order: mature solution > compatible OSS > fork/modify > custom.
10. EXISTING SOFTWARE — research options for shell, compositor, file manager, settings, terminal, notifications, launcher, package UI, task manager, system monitor, screenshot, archiver, text editor, display manager, network, Bluetooth, audio, updates.
11. LICENSING — record project, version, source, license, modifications, redistribution requirements; create THIRD_PARTY_LICENSES.md.
12. DEV ENVIRONMENT — reproducible: Git, versioned builds, automated build scripts, reproducible config, automated tests, VM tests, hardware tests. Never destroy last known-good without backup/commit.
13. VM FIRST — BUILD → BOOT VM → FUNCTIONAL → UI → PERFORMANCE → LOG ANALYSIS → FIX → RETEST, then hardware.
14. AUTONOMOUS DEV LOOP (13 steps) — DEFINE, RESEARCH, PLAN, IMPLEMENT (smallest useful increment), BUILD, TEST, OBSERVE (logs/crashes/CPU/RAM/GPU/disk/UI/behaviour), COMPARE, FIX, REGRESSION TEST, OPTIMIZE (after correctness), VERIFY, ITERATE.
15. NO FALSE SUCCESS — compile/boot/screenshot ≠ done. Done = implementation + build + functional test + regression test + verification.
16. COMMUNICATION — per iteration report: CURRENT OBJECTIVE, RESEARCH, DECISION, IMPLEMENTATION, TEST, RESULT, PROBLEMS, FIX, METRICS, NEXT. No claims without evidence.
17. PHASE 0 — FIRST MISSION: research & architecture only. Compare bases, desktop architectures, compositors, GUI toolkits, app technologies, packaging, update architectures, installers, Windows compat tech, performance strategies. Deliver: (1) recommended Linux base, (2) complete architecture, (3) tech stack, (4) component dependency graph, (5) roadmap, (6) risk assessment, (7) performance strategy, (8) security strategy, (9) testing strategy, (10) initial prototype plan.

IMPORTANT: Part 1 of 5. No massive implementation yet. Wait for parts 2–5, then merge all five into one complete Raven OS specification.
