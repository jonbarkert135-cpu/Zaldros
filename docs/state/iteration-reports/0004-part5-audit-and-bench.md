# Iteration report 0004 — PART 5 integrated, combined-spec audit, benchmark harness

Format per spec PART 1 §16. Date: 2026-08-23.

**CURRENT OBJECTIVE** — Close the specification: absorb PART 5, then do what PART 5 actually asks for
first (§25.2, §25.3) — audit the combined PARTS 1–5 for contradictions, gaps and risks — and build the
measurement harness §1 requires, since without it every later optimization claim would be unfounded.

**RESEARCH** — Read all five parts as one document. The interesting finding is that the parts
*disagree* in six places, most importantly: PART 1 §8 wants aggressive performance profiles while
PART 4 §6 forbids removing drivers and PART 5 §2 forbids disabling essential services; and PART 2 wants
close Windows fidelity while PART 5 §16 ranks visual similarity 7th of 8 priorities. Implementing
either part literally would violate the other.

**DECISION** — `docs/SPEC_AUDIT.md`: six contradictions resolved explicitly (profiles are runtime-only;
fidelity yields to stability and is documented as deviations, not hidden; immutable base + Flatpak
reconciles "install anything"; phases renumbered to the spec's 0–14; narrow tested tooling satisfies
both "research first" and "start now"; PowerShell 7 is MIT so it is legal but optional). Eight genuine
gaps recorded — Secure Boot strategy, localization, accessibility, project license, the name collision,
update bandwidth, encryption default, crash reporting without telemetry — with a proposal for each and
seven questions escalated to the owner.

**IMPLEMENTATION** — `spec/PART_5.md`; `docs/SPEC_AUDIT.md`; `docs/architecture/FEATURE_MATRIX.md`
(PART 5 §18, everything honestly NOT IMPLEMENTED or PARTIALLY IMPLEMENTED); roadmap renumbered to
phases 0–14; the full §14 document set (BUILD, INSTALL, RECOVERY, COMPATIBILITY, CONTRIBUTING,
CHANGELOG + root pointers for ARCHITECTURE/SECURITY/PERFORMANCE). New component
`tools/zaldros-bench` v0.1.0: collects used RAM, load, process count, running services and all six
systemd boot stages, and implements BASELINE → CHANGE → BENCHMARK → COMPARE → ACCEPT/REVERT as a
`decide()` function with a 3 % noise threshold.

**TEST** — 13 new unit tests: duration parsing (ms/s/min), systemd-analyze stage extraction, meminfo
and used-RAM computation, loadavg, process counting, the "unavailable metrics are labelled with a
reason" invariant, noise threshold, accept on improvement, revert on any regression, INCONCLUSIVE when
a metric is missing, markdown rendering and both CLI paths including `--strict` exit codes.

**RESULT** — `44 passed in 0.19s`. Live run in this environment returned used_ram 31.3 MiB,
process_count 13, and correctly reported all six boot metrics and the service count as `null` with the
reason "systemd-analyze unavailable (no systemd in this environment)".

**PROBLEMS** — The environment cannot produce a meaningful baseline: no systemd, no podman, no KVM.
A harness that silently reported partial data would produce fake optimization wins later.

**FIX** — Missing measurements are first-class: `null` plus a reason string, and `decide()` returns
INCONCLUSIVE rather than ACCEPT whenever any metric is missing, so an unmeasured metric can never be
counted as an improvement. The CI baseline job runs the same harness on a real systemd runner.

**METRICS** — 44/44 tests, 0.19 s. Four shipping tools, zero external dependencies. Evidence records:
still 0 — no image has booted.

**NEXT** — Phase 1 the moment a build host exists: build `zaldros-base`, boot in QEMU, capture the
first service map, hardware inventory and performance baseline. Meanwhile the seven questions in
`SPEC_AUDIT.md` §E block decisions that are cheap now and expensive later (project license, name,
Secure Boot).

---

## Addendum — owner decisions closed (2026-08-23)

**DECISION** — ADR-0005 records four owner decisions, each benchmarked against what Ubuntu, Debian,
Arch and Mint actually do: name **Zaldros OS** (short-name convention kept; suffix changed from "Linux"
to "OS" only to avoid the live zaldroslinux.org project); license **GPL-3.0-or-later** for our own code
with forks keeping upstream licenses; **Russian default with first-class English** plus a tier-2
language set, and a hard no-hardcoded-strings rule from the first line of shell code; disk encryption
**off by default**, offered as an installer checkbox — which is exactly what Ubuntu, Mint and Debian do
(Fedora is the outlier here).

**RESEARCH** — The owner also questioned the Fedora bootc base. `docs/research/03-base-distribution-reopened.md`
reopens ADR-0001 honestly: Fedora bootc is not obscure (it is Fedora, packaged as an image), but for the
stated goal of maximum device coverage plus familiarity, the Debian family wins on old hardware, NVIDIA
packaging, `.deb` third-party software and documentation volume, while Ubuntu LTS + HWE closes most of
the fresh-kernel gap. Recommendation: default to an **Ubuntu 24.04 LTS + HWE** base, at the cost of
rebuilding atomic rollback ourselves with btrfs snapshots + grub-btrfs.

**PROBLEMS** — This must not become an opinion flip-flop, and `LICENSE` could not be completed: the
sandbox has no network access, so the verbatim GPL-3.0 text could not be fetched. The file carries the
SPDX identifier and the standard notice with an explicit marker that the full text must be pasted
before release.

**FIX / NEXT** — The base decision is settled by a defined test, not by preference: build both minimal
images, boot each on the weakest available machine, and record `zaldros-hwinfo`, `zaldros-bench collect`
and a deliberate broken-update rollback. All four tools are base-agnostic, so no work is lost either
way. The test needs CI or a real machine — still the project's only blocker.
