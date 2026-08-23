# Iteration report 0002 — PART 3 integrated, hardware inventory backend

Format per spec PART 1 §16. Date: 2026-08-23.

**CURRENT OBJECTIVE** — Absorb specification PART 3 (system applications) into the live project
without restarting it, decide build-vs-reuse for every application, and ship the next real component.

**RESEARCH** — Evaluated existing Qt/KDE applications against each PART 3 requirement. Findings:
Dolphin (KIO) already covers the great majority of Explorer's feature list including network
locations and trash; Konsole covers tabs, split panes and profiles; Spectacle and Ark cover
screenshots and archives; PowerShell 7 is MIT-licensed and cross-platform, so it can be offered as a
Terminal profile with no proprietary components. Conversely, KDE System Settings cannot be
re-arranged into the Windows-11 Settings structure, and Kate is heavier than PART 3 §4 allows.

**DECISION** — Recorded in `docs/architecture/SYSTEM_APPS.md`: fork/reskin Dolphin for Explorer;
reuse Konsole, Spectacle, Ark, mpv, Firefox; build custom (Qt6/QML) Settings, Update Center,
Notepad, Task Manager + Resource Monitor (one binary), Device Manager, Disk Management (UI over
udisks2), Event Viewer (over journald), Services (over systemd + the §7 service map), System
Information, Startup Apps, Firewall (over firewalld), Recovery (over bootc/ostree rollback).
Per-application quality gates set (cold start, idle RSS, zero background processes when closed).

**IMPLEMENTATION** — `spec/PART_3.md` preserved; `docs/architecture/SYSTEM_APPS.md` added;
project state and CI updated. New component `tools/bedrock-hwinfo` v0.1.0: the read-only backend for
Device Manager and System Information — CPU, memory, storage, network, displays, batteries,
board/firmware identity, kernel and OS, read from `/proc` and `/sys` only, with `--sysfs`/`--proc`
overrides so it is testable without root or special hardware.

**TEST** — 10 new unit tests against a synthetic `/sys` and `/proc` tree: loop/ram devices excluded,
loopback interface excluded, wireless detection, DRM connector filtering, battery-only power
supplies, sector→byte conversion, uptime parsing, and both report renderers. One test specifically
asserts the honesty rule: with no readable sources the report says `unknown` and contains no
fabricated vendor strings.

**RESULT** — `20 passed in 0.10s` across both tools. Live run on this host produced a correct
inventory (Debian 12 container, AMD CPU, 17 logical cores) and correctly reported board, firmware,
disks and displays as unknown/empty rather than inventing them — exactly the §21 behaviour.

**PROBLEMS** — This host is a container: no DMI, no block devices, no DRM, so the storage/display
paths could not be exercised against real hardware here.

**FIX** — Those paths are covered by fixture-based tests now, and CI runs the tool on a real VM
runner and publishes the inventory as an artefact; a physical-hardware run happens in Phase 1's
VM/hardware matrix.

**METRICS** — 20/20 tests, 0.10 s. External dependencies: still zero. Two shipping tools.

**NEXT** — `Containerfile` for `bedrock-base` and `bedrock-desktop` plus a QEMU boot smoke test —
this is the first step that genuinely needs a Linux build host with KVM.
