# Bedrock OS

A Linux desktop operating system built around **Windows-11-familiar workflows**, with a clean,
lightweight and aggressively optimised Linux system underneath.

> Not "Linux with a Windows theme" — a complete Linux desktop environment designed around
> Windows-familiar workflows.

**Name:** the official project name is **Bedrock OS**. The master-specification text uses
"Raven OS"; that name was invented by the AI that drafted the spec and is superseded — see
[`docs/NAMING.md`](docs/NAMING.md).

## Status

| | |
|---|---|
| Phase | **Phase 0 — Research & Architecture** (in progress) |
| Spec parts received | 1, 2 of 5 |
| Current milestone | Foundation: architecture decisions + first tooling |

Live state lives in [`docs/state/PROJECT_STATE.md`](docs/state/PROJECT_STATE.md).

## Repository layout

```
spec/                  Master specification parts as received (source of truth for requirements)
docs/research/         Evidence-based comparisons (base distro, compositor, toolkit, ...)
docs/architecture/     Architecture, tech stack, dependency graph, roadmap, risks, strategies
docs/state/            Living project state, decision log (ADRs), iteration reports
tools/bedrock-sysprobe/ Service & resource probe — produces the service/dependency map (spec §7)
assets/refs/           UX reference material
```

## Principles (from the master specification)

1. Research first: mature OSS > compatible OSS > fork > custom.
2. Performance first: BASELINE → CHANGE → MEASURE → COMPARE → ACCEPT/REVERT.
3. No false success: build + functional test + regression test + verification, or it is not done.
4. Legal: no proprietary Microsoft code, binaries, fonts, icons or wallpapers in this repository.
5. VM first: every system-level change is validated in a VM before hardware.

## License

Project code: see `LICENSE` (to be finalised). Third-party components are tracked in
[`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md).
