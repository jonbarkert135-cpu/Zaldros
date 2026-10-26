# Naming — AUTHORITATIVE

**Official name: Zaldros OS** — decided by the owner (Linussi Fril) on 2026-08-23 after the full
name-availability audit in `docs/NAME_RESEARCH.md` (129 names checked). See ADR-0006.

## Canonical forms

| Context | Form |
|---|---|
| Product name | **Zaldros OS** |
| Alternative long form | Zaldros Linux (acceptable in prose; "Zaldros OS" is preferred) |
| Short identifier | `zaldros` — `ID=zaldros` in `/etc/os-release` |
| Package prefix | `zaldros-*` (e.g. `zaldros-shell`, `zaldros-settings`) |
| Python/module prefix | `zaldros_*` |
| CLI tools | `zaldros-sysprobe`, `zaldros-hwinfo`, `zaldros-compat`, `zaldros-bench` |
| Desktop shell | Zaldros Desktop Shell (Taskbar, Start, System Applications) |
| Performance profiles | Zaldros Desktop / Zaldros Performance / Zaldros Legacy |
| Domains (to register) | `zaldros.org` primary, `.com`/`.io`/`.dev` defensive |
| Namespaces (to claim) | `github.com/zaldros`, GitLab `zaldros`, Codeberg `zaldros` |

## Withdrawn names — do not use

- **Bedrock OS / Bedrock Linux** — collides with Bedrock Linux (active meta-distribution since 2009,
  bedrocklinux.org), Minecraft Bedrock Edition and BedRock Systems. 🔴 RED.
- Prime / Nova / Aurora / Basalt / Polaris / Phoenix — all 🔴 RED, see `docs/NAME_RESEARCH.md`.

Use the canonical Zaldros forms above throughout the specification, interface and documentation.

## Open item

Trademark clearance (USPTO / EUIPO / Роспатент, classes 9 and 42) is **not** done — the audit was a
public web and registry search only. **LEGAL REVIEW REQUIRED** before any public brand launch.
Fallback names if clearance fails: Quinvara, then Oskuria.
