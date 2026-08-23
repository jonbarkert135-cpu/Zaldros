# Iteration report 0001 — Phase 0 foundation

Format per spec PART 1 §16. Date: 2026-08-23.

**CURRENT OBJECTIVE** — Leave "reading the spec" mode: establish the project in the repository,
make the Phase 0 architecture decisions with evidence, and ship the first genuinely useful component.

**RESEARCH** — Compared base distributions (Debian / Ubuntu / Arch / Fedora / Fedora-bootc /
minimal bases) and desktop architectures (KWin+Plasma / GNOME / smithay / wlroots) and toolkits
(Qt6 / GTK4 / Rust GUI / Electron). Key findings: `bootc` is a CNCF Sandbox project with official
Fedora base images, read-only `/usr`, atomic updates and rollback, already used by shipping
distributions (Bluefin, Universal Blue); smithay is production-capable but is a low-level
building-block library — Xfce's own Wayland compositor built on it is a multi-year roadmap; existing
Windows-11-style Linux desktops (Wubuntu, KDE "Windows Modern") all reach parity on Plasma, showing
KWin does not obstruct Windows workflows. Full write-ups in `docs/research/`.

**DECISION** — Fedora bootc base (ADR-0001); KWin 6 Wayland compositor (ADR-0002); Qt6/QML for our
own shell and system apps, Rust for new daemons (ADR-0003); btrfs+zstd+zram (ADR-0004). Explicitly
*not* a theme pack: the taskbar, Start, search, quick settings and settings app are our components.

**IMPLEMENTATION** — Repository scaffolded: `spec/` (parts 1–2 verbatim), `docs/research`,
`docs/architecture` (architecture, roadmap, risks, performance, security, testing),
`docs/state` (project state, 4 ADRs, this report), `THIRD_PARTY_LICENSES.md`, CI workflow.
First component: `tools/bedrock-sysprobe` v0.1.0 — a standard-library Python tool that produces the
service/dependency/resource map required by PART 1 §7 (description, state, enablement, PSS RAM,
CPU seconds, `systemd-analyze blame` boot cost, dependants, "is anything requiring it").

**TEST** — 11 unit tests over the parsers (`systemctl show`, `systemd-analyze blame` incl. min/s/ms
scaling), PSS reading from a fake `/proc`, dependant de-duplication, the disable-safety rule, and both
report renderers. Plus a live CLI run.

**RESULT** — `11 passed in 0.04s`. Live run in this sandbox exits cleanly with a clear diagnostic
because the sandbox has no systemd; CI runs the same command on a real systemd host and publishes the
generated map as a build artefact.

**PROBLEMS** — (1) No systemd and no VM/KVM in the current environment, so a real service map and
real boot/RAM baselines cannot be produced here. (2) Spec PART 3 was referenced by the owner but never
arrived in chat, so decisions are based on PARTS 1–2 only.

**FIX** — (1) Live probing moved into CI (`ubuntu-latest` is a real systemd host) so the map is
produced on every push; a QEMU boot job is the next milestone. (2) Requested PART 3 from the owner;
all documents are additive so later parts extend rather than restart the project.

**METRICS** — Unit tests 11/11 passing, runtime 0.04 s. Dependencies added: zero (standard library
only, so the tool runs inside a minimal image). System metrics: none yet — no baseline can honestly be
claimed without a VM run.

**NEXT** — `Containerfile` for `bedrock-base` (core system, no shell) and `bedrock-desktop`, built in
CI, then a QEMU boot smoke test that attaches the service map and the first real baseline
(boot time, idle RAM, idle CPU) to the build.
