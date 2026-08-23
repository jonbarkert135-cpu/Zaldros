# ADR-0006 — Project name: Zaldros OS

Date: 2026-08-23 · Status: **Accepted** (owner decision) · Supersedes: ADR-0005 §1

## Context

The working names used so far ("RAVEN OS" from the spec prompt, then "Bedrock OS" from ADR-0005) were
never verified. A full name-availability audit of **129 candidates** was run: RDAP queries to the
`.com`/`.org`/`.io`/`.dev` registries, namespace probes on GitHub / GitLab / Codeberg, GitHub Search,
and web verification against DistroWatch, Wikipedia, company registries and product sites.
Full record: `docs/NAME_RESEARCH.md`.

Result: every previously considered name is 🔴 RED.

- Bedrock — Bedrock Linux (active meta-distribution since 2009, v0.7.31, Wikipedia), Minecraft
  Bedrock Edition, BedRock Systems.
- Raven — Raven-OS (raven-os.org), RavenOS (Arch-based), Raven Resonance.
- Prime — PrimeOS (Android-x86), Prime GNU/Linux. Nova — Nova GNU/Linux (Cuba), OpenStack Nova.
- Aurora — Aurora OS (Russian mobile OS) and Aurora by Universal Blue. Basalt — BasaltOS.
  Polaris — Linux Polaris. Phoenix — PhoenixOS, Phoenix BIOS.

## Decision

The project is named **Zaldros OS**; short identifier `zaldros`.

Rationale: it is the only candidate of the 129 with zero conflicts in every checked category — no
distribution, OS, desktop environment, kernel/system component, package, company or notable OSS
project, and 0 repositories in GitHub Search. `.com`, `.org`, `.io` and `.dev` are all available, as
are `github.com/zaldros`, `github.com/zaldroslinux`, GitLab and Codeberg. Phonetically it reads the
same in Russian and English and carries no negative meaning in the major languages.

Reserve names if trademark clearance fails: **Quinvara**, then **Oskuria**.

## Consequences

- Repository-wide rename: `ID=zaldros`, package prefix `zaldros-*`, modules `zaldros_*`,
  CLI `zaldros-sysprobe|hwinfo|compat|bench`, shell at `shell/zaldros-shell`, QML `ZaldrosTheme`.
- `docs/NAMING.md` rewritten as the authoritative naming reference.
- `docs/NAME_RESEARCH.md` deliberately keeps the Bedrock/Raven names — it is the audit record and
  must name the conflicting projects explicitly.
- The Git repository itself is still `bedrock_os` on GitHub; renaming it is an owner action
  (GitHub redirects the old URL, so it is safe to do at any time).
- `.github/workflows/ci.yml` cannot be pushed by the automation (missing `workflows` permission);
  the updated version with the new paths lives in `docs/ci/ci.yml` and must be copied in manually.
- **LEGAL REVIEW REQUIRED**: trademark clearance (USPTO / EUIPO / Роспатент, classes 9 and 42) is
  outstanding. The audit was a public search, not a legal opinion.
