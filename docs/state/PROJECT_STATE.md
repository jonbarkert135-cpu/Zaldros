# Project state

```
Base:          Ubuntu 26.04 LTS
Status:        PROPOSED
ISO:           BUILT - run #24 (60e478b), all 3 variants x 3 profiles
Boot:          FAIL - 9/9 combinations, failed_checks = ["shell"].
               PASS: kernel 7.0.0-30-generic, systemd, Wayland socket, KWin,
               autologin session, konsole launch 2.0 s, 0 failed units.
               FAIL: the Zaldros shell exits at startup.
               Root cause (from /tmp/zaldros-session.log, not guessed):
               FileNotFoundError /opt/zaldros/data/pinned.json - build-iso.sh
               never copied shell/zaldros-shell/data into the image.
               run 32675722125, 2026-08-24.
Architecture:  NOT ACCEPTED - no variant has shown the Zaldros shell on screen yet.
               The RAM figures below are KWin-only sessions, so they do not
               compare the three architectures.
Idle RAM (QEMU, low profile): full 479 MiB / 24 proc, services 440 MiB / 21 proc,
               legacy 462 MiB / 21 proc - comparison data only, not hardware evidence.
Boot time:     MEASURED (QEMU) - uptime at self-test 21.6-24.3 s across all 9
               combinations; systemd-analyze still empty while systemd is "starting".
```

_Last updated: 2026-08-24_

| Field | Value |
| --- | --- |
| Project | Zaldros OS |
| Phase | 0 — Research & Architecture |
| Spec parts received | **all 5 of 5** (complete specification) |
| Base decision | Ubuntu 26.04 LTS `resolute`, live ISO (ADR-0009, **PROPOSED** — accepted only after a real build + boot). Supersedes ADR-0001 Fedora bootc. |
| Desktop decision | KWin 6 (Wayland) + own Zaldros shell components in Qt6/QML (ADR-0002, ADR-0003) |
| Reality audit | `docs/REALITY_AUDIT.md` — project was documentation+backend only until 2026-08-23 |
| Shipping code | `zaldros-sysprobe`, `zaldros-hwinfo`, `zaldros-compat`, `zaldros-bench` (all v0.1.0) + `shell/zaldros-shell` prototype — 44 tool tests + 9 shell tests passing |
| Blocked on | a Linux build host with podman + /dev/kvm (or enabled GitHub Actions) — needed to build and boot the images and to record any hardware evidence |

## Done
- Specification parts 1–2 preserved verbatim in `spec/`
- Naming authority recorded (`docs/NAMING.md`): official name **Zaldros OS**, not "Zaldros OS"
- Base distribution research and decision
- Desktop/compositor/toolkit research and decision
- Architecture, roadmap, risks, performance, security and testing strategies
- First component built and tested: `zaldros-sysprobe`
- CI: unit tests + live service-map and hardware-inventory runs on a real systemd host, artefacts published
- PART 3 integrated: `docs/architecture/SYSTEM_APPS.md` — build/reuse decision for every system app
- Second component: `tools/zaldros-hwinfo` v0.1.0 (Device Manager / System Information backend)
- PART 4 integrated: `docs/architecture/COMPATIBILITY_AND_HARDWARE.md`
- Third component: `tools/zaldros-compat` v0.1.0 — compatibility registries with a CI evidence gate
- `build/Containerfile.base` + `build/Containerfile.desktop` written (**never built — no build host**)
- PART 5 integrated: combined-spec audit (`docs/SPEC_AUDIT.md`), feature matrix, roadmap renumbered to phases 0–14
- Fourth component: `tools/zaldros-bench` v0.1.0 — baseline/compare harness (PART 5 §1)
- Spec §14 document set complete: README, ARCHITECTURE, BUILD, INSTALL, RECOVERY, SECURITY, PERFORMANCE, COMPATIBILITY, CONTRIBUTING, THIRD_PARTY_LICENSES, CHANGELOG

## Next
1. Answers to the 7 open questions in `docs/SPEC_AUDIT.md` §E (name, license, locale, encryption default, Secure Boot, build host, reference hardware).
2. `Containerfile` for `zaldros-base` (core, no shell) + `zaldros-desktop`, built in CI.
3. QEMU boot smoke test; attach the `zaldros-sysprobe` map and baseline metrics to the build.
4. Turn the map into the three performance profiles as systemd presets.

## Open questions for the owner
- **Name collision:** an unrelated project zaldroslinux.org already uses "Zaldros OS". Keep it or
  differentiate before release?
- Target hardware for the first baseline (which machine defines "reference laptop")?
- Is a Linux build host / self-hosted runner available for image builds and VM tests?

- Run #18: all CI jobs green, boot=FAIL on all 9 (systemd/app_launch), root causes fixed in run #19 candidate. Architecture: NOT ACCEPTED. [ci run 32670157459, 2026-08-23]
- Run #24: iso + CI green, boot=FAIL on all 9 (`shell`) — the ISO never shipped `data/pinned.json`.
  Fixed in the run #25 candidate together with a flat-layout guard test. [ci run 32675722125, 2026-08-24]
