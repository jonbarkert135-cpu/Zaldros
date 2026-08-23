# Project state

_Last updated: 2026-08-23_

| Field | Value |
| --- | --- |
| Project | Bedrock Linux |
| Phase | 0 — Research & Architecture |
| Spec parts received | 1, 2, 3 of 5 |
| Base decision | Fedora, bootc/bootable-container flavour (ADR-0001) |
| Desktop decision | KWin 6 (Wayland) + own Bedrock shell components in Qt6/QML (ADR-0002, ADR-0003) |
| Shipping code | `tools/bedrock-sysprobe` v0.1.0, `tools/bedrock-hwinfo` v0.1.0 — 20 unit tests passing |
| Blocked on | a Linux build host / VM runner for image builds and real measurements |

## Done
- Specification parts 1–2 preserved verbatim in `spec/`
- Naming authority recorded (`docs/NAMING.md`): official name **Bedrock Linux**, not "Raven OS"
- Base distribution research and decision
- Desktop/compositor/toolkit research and decision
- Architecture, roadmap, risks, performance, security and testing strategies
- First component built and tested: `bedrock-sysprobe`
- CI: unit tests + live service-map and hardware-inventory runs on a real systemd host, artefacts published
- PART 3 integrated: `docs/architecture/SYSTEM_APPS.md` — build/reuse decision for every system app
- Second component: `tools/bedrock-hwinfo` v0.1.0 (Device Manager / System Information backend)

## Next
1. Integrate PARTS 4–5 when they arrive — additive, no restart.
2. `Containerfile` for `bedrock-base` (core, no shell) + `bedrock-desktop`, built in CI.
3. QEMU boot smoke test; attach the `bedrock-sysprobe` map and baseline metrics to the build.
4. Turn the map into the three performance profiles as systemd presets.

## Open questions for the owner
- **Name collision:** an unrelated project bedrocklinux.org already uses "Bedrock Linux". Keep it or
  differentiate before release?
- Target hardware for the first baseline (which machine defines "reference laptop")?
- Is a Linux build host / self-hosted runner available for image builds and VM tests?
