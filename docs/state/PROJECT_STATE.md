# Project state

_Last updated: 2026-08-23_

| Field | Value |
| --- | --- |
| Project | Bedrock OS |
| Phase | 0 — Research & Architecture |
| Spec parts received | **all 5 of 5** (complete specification) |
| Base decision | Fedora, bootc/bootable-container flavour (ADR-0001) |
| Desktop decision | KWin 6 (Wayland) + own Bedrock shell components in Qt6/QML (ADR-0002, ADR-0003) |
| Reality audit | `docs/REALITY_AUDIT.md` — project was documentation+backend only until 2026-08-23 |
| Shipping code | `bedrock-sysprobe`, `bedrock-hwinfo`, `bedrock-compat`, `bedrock-bench` (all v0.1.0) + `shell/bedrock-shell` prototype — 44 tool tests + 9 shell tests passing |
| Blocked on | a Linux build host with podman + /dev/kvm (or enabled GitHub Actions) — needed to build and boot the images and to record any hardware evidence |

## Done
- Specification parts 1–2 preserved verbatim in `spec/`
- Naming authority recorded (`docs/NAMING.md`): official name **Bedrock OS**, not "Raven OS"
- Base distribution research and decision
- Desktop/compositor/toolkit research and decision
- Architecture, roadmap, risks, performance, security and testing strategies
- First component built and tested: `bedrock-sysprobe`
- CI: unit tests + live service-map and hardware-inventory runs on a real systemd host, artefacts published
- PART 3 integrated: `docs/architecture/SYSTEM_APPS.md` — build/reuse decision for every system app
- Second component: `tools/bedrock-hwinfo` v0.1.0 (Device Manager / System Information backend)
- PART 4 integrated: `docs/architecture/COMPATIBILITY_AND_HARDWARE.md`
- Third component: `tools/bedrock-compat` v0.1.0 — compatibility registries with a CI evidence gate
- `build/Containerfile.base` + `build/Containerfile.desktop` written (**never built — no build host**)
- PART 5 integrated: combined-spec audit (`docs/SPEC_AUDIT.md`), feature matrix, roadmap renumbered to phases 0–14
- Fourth component: `tools/bedrock-bench` v0.1.0 — baseline/compare harness (PART 5 §1)
- Spec §14 document set complete: README, ARCHITECTURE, BUILD, INSTALL, RECOVERY, SECURITY, PERFORMANCE, COMPATIBILITY, CONTRIBUTING, THIRD_PARTY_LICENSES, CHANGELOG

## Next
1. Answers to the 7 open questions in `docs/SPEC_AUDIT.md` §E (name, license, locale, encryption default, Secure Boot, build host, reference hardware).
2. `Containerfile` for `bedrock-base` (core, no shell) + `bedrock-desktop`, built in CI.
3. QEMU boot smoke test; attach the `bedrock-sysprobe` map and baseline metrics to the build.
4. Turn the map into the three performance profiles as systemd presets.

## Open questions for the owner
- **Name collision:** an unrelated project bedrocklinux.org already uses "Bedrock OS". Keep it or
  differentiate before release?
- Target hardware for the first baseline (which machine defines "reference laptop")?
- Is a Linux build host / self-hosted runner available for image builds and VM tests?
