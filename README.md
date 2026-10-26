# Zaldros OS

A Linux desktop operating system built around **Windows-11-familiar workflows**, with a clean,
lightweight and aggressively optimised Linux system underneath.

The goal is a complete Linux desktop environment designed around Windows-familiar workflows.
The current implementation is a prototype; a complete everyday OS is not yet verified.

**Name:** the official project name is **Zaldros OS**. The master-specification text uses
"Raven OS" in historical requirements maps to Zaldros OS — see
[`docs/NAMING.md`](docs/NAMING.md).

## Status

| | |
|---|---|
| Current target | **Developer alpha**: real Linux workflows, not only offscreen UI |
| Spec parts received | All 5 parts, preserved in `spec/` |
| Implemented foundation | Qt/QML shell, Python backend, system tools, Office bridges, ISO/VM scripts |
| Verified locally | Tools: 44 passed; shell/backend audit: 514 passed, 1 skipped; real system/VM/hardware checks remain separate |
| Current cycle | P01 capability inventory complete; P02 clean-room and trusted rootfs preparation next |

See the [capability register](docs/development/CAPABILITIES.md) for implementation gaps,
test environments and unverified behavior. A successful mock-service test does not prove
that the corresponding real Linux service works end to end.

Live state lives in [`docs/state/PROJECT_STATE.md`](docs/state/PROJECT_STATE.md).
The [development plan and 20 task prompts](docs/development/README.md) define the next work.

## Repository layout

```
spec/                  Master specification parts as received (source of truth for requirements)
docs/research/         Evidence-based comparisons (base distro, compositor, toolkit, ...)
docs/architecture/     Architecture, tech stack, dependency graph, roadmap, risks, strategies
docs/state/            Living project state, decision log (ADRs), iteration reports
docs/development/      Current audit, capability register, plan, prompts and handoff
backend/               Linux service adapters and D-Bus transport
shell/zaldros-shell/   Qt/QML shell and backend tests
apps/                  Writer, Sheets and Slides backed by LibreOffice
tools/                 sysprobe, hwinfo, compatibility registry, benchmarks and diagnostics
build/iso/             Ubuntu live ISO build and QEMU verification scripts
assets/refs/           UX reference material
```

## Principles (from the master specification)

1. Research first: mature OSS > compatible OSS > fork > custom.
2. Performance first: BASELINE → CHANGE → MEASURE → COMPARE → ACCEPT/REVERT.
3. No false success: build + functional test + regression test + verification, or it is not done.
4. Legal: no proprietary Microsoft code, binaries, fonts, icons or wallpapers in this repository.
5. VM first: every system-level change is validated in a VM before hardware.

## License

Zaldros's own code: GPL-3.0-or-later, see `LICENSE` and `CONTRIBUTING.md`.
Third-party components retain their licenses and are tracked in
[`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md).
