# Zaldros OS

A Linux desktop operating system built around **Windows-11-familiar workflows**, with a clean,
lightweight and aggressively optimised Linux system underneath.

The goal is a complete Linux desktop environment designed around Windows-familiar workflows.
The current implementation is a prototype; a complete everyday OS is not yet verified.

**Name:** the official project name is **Zaldros OS**. See
[`docs/NAMING.md`](docs/NAMING.md) for canonical forms.

## Status

| | |
|---|---|
| Current target | **Developer alpha**: real Linux workflows, not only offscreen UI |
| Spec parts received | All 5 parts, preserved in `spec/` |
| Implemented foundation | Qt/QML shell, Python backend, system tools, Office bridges, ISO/VM scripts |
| Verified locally | Tools: 44 passed; current shell/backend suite: 587 passed, no skips; real system/VM/hardware checks remain separate |
| Current cycle | P01 complete; P02 rootfs authentication verified against Ubuntu; vendored-asset licensing reviews remain open |

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

---

## Development status and contributors

### What Zaldros OS is building

Zaldros OS is an independent, experimental Linux desktop project. Its goal is to
combine familiar Windows-style workflows with Linux applications and system services.
It uses a proposed Ubuntu 26.04 base, KWin 6 on Wayland, a Qt/QML shell and a Python
backend. KDE components provide parts of the desktop infrastructure; they do not
constitute a completed isolation or security architecture.

The repository contains working local tools, a desktop prototype, system-service
adapters, LibreOffice-backed application prototypes and live-ISO build/test scripts.
These parts still need substantial integration and testing. Passing unit tests,
mock-service tests or producing a screenshot does not establish that the complete
system works on a computer. See the [capability register](docs/development/CAPABILITIES.md)
for what has actually been checked.

### Maintainer and resources

I started this project with extensive assistance from AI. I am not a professional
operating-system developer, and I cannot independently complete or maintain a system
of this scope. Development has previously been interrupted by limited access to AI
resources and API credits, as well as a lack of dedicated test hardware.

Work has resumed through the [staged development plan](docs/development/PLAN.md),
but progress depends on available resources and help from experienced contributors.
The project has not been abandoned. There is no promised release date.

### Experimental builds

CI has produced three ISO variants and verified nine VM boots for the source
revision recorded in the [build evidence](docs/state/evidence/p02-rootfs/README.md).
Earlier results exposed failed screenshot checks in the minimal variant. The
current gate rejects failed or missing required UI results, and screenshot runtime
is included in every variant. Physical-hardware support, installation, updates and recovery are not yet
comprehensively verified. Some controls and features are incomplete.

Start with a virtual machine. If testing on physical hardware, use a dedicated test
computer and back up its data. A live ISO is not evidence of a finished installer,
and an experimental build should not be relied on for important work.

### How to contribute

Help is especially useful with Linux system integration, KWin/Wayland, Qt/QML,
asynchronous backend operations, packaging, boot and installation, security,
accessibility, translation and testing on real hardware.

- Pick a documented gap from the [development plan](docs/development/PLAN.md).
- Report reproducible problems with the source commit, environment, steps and logs.
  Remove passwords, tokens and personal information before sharing diagnostics.
- Submit focused pull requests with a clear explanation and relevant tests.
- Review the architecture, improve documentation or contribute hardware test reports.
- Help verify the provenance and licensing of third-party components.

Please read [CONTRIBUTING.md](CONTRIBUTING.md). Contributions are reviewed for
correctness, maintainability and alignment with the project. Suggestions and test
reports are welcome even when a fix cannot be implemented immediately.

### Funding and support

The current provisional funding target is **US $5,300**. This is the maintainer's
initial estimate, not a priced bill of materials, a fixed requirement or a promise
that this amount will produce a finished operating system. It may change when
hardware requirements and actual costs are established.

Support would help pay for development and test hardware, peripherals for
compatibility testing, AI API credits and build infrastructure. Financial support
is voluntary and does not guarantee a feature, release date or development outcome.

**Bitcoin (BTC) — Bitcoin mainnet**

```text
bc1qqurk33dc8d8xuy0cqrlylqzx6amvt2agy2hzcv
```

Check the address and network before sending. Bitcoin transfers are generally
irreversible. Do not use another cryptocurrency or network for this address.

Code, reviews, documentation and reliable test results are equally valuable ways
to support Zaldros OS. The immediate goal is a usable, testable Linux developer
alpha; the longer-term goal is a stable desktop system that people can use without
needing to learn system administration first.
