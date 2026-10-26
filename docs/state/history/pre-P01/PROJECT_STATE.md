# Project state

```
Base:          Ubuntu 26.04 LTS
Status:        PROPOSED
ISO:           BUILT - run #25 (773c1f4), all 3 variants x 3 profiles
Boot:          PASS - 9/9 combinations, failed_checks = [].
               Verified per combination: kernel 7.0.0-30-generic, systemd with
               0 failed units, /run/user/1000/wayland-0, kwin_wayland, autologin
               session, the Zaldros shell drawing on screen (QMP screenshots),
               konsole launch 2.0 s.
               run 32991329542, 2026-08-26.
Architecture:  NOT ACCEPTED YET - the three variants now boot identically, so the
               comparison is finally possible, but it needs one run with the UI
               interaction test believed (see below) before a variant is chosen.
Idle RAM (QEMU, run #25): full 655 MiB / 26 proc, services 606 MiB / 23 proc,
               legacy 606 MiB / 23 proc (low profile) - shell + KWin, no plasmashell.
               Comparison data under emulation, not hardware evidence.
Boot time:     MEASURED (QEMU) - uptime at self-test 21.3-24.3 s across all 9
               combinations; systemd-analyze still empty while systemd is "starting".
UI test:       NOT TRUSTWORTHY in run #25 - the window query read the wrong log and
               the host driver clicked a guessed point, so it reported FAIL against a
               working shell. Fixed in run #26; verdicts before it are void.
```

_Last updated: 2026-08-26_

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
- Run #27 (visual parity cycle 1): Windows 11 geometry measured into `system/theme/win11-reference.json`; `tools/visual/parity.py` reports 29/29 component checks matching; Explorer and Settings became real applications. Boot verdict unchanged from run #25 (PASS 9/9). [local render + pytest, 2026-08-26]
- Диспетчер задач (ADR-0016): процессы, ЦП/память/диск/сеть/GPU/автозагрузка из `/proc` и sysfs;
  закрытое окно не делает ни одного чтения (проверено тестом). Семь кадров попиксельно идентичны
  HEAD `89975d5`, паритет 41/41, shell 372 passed + 1 skipped, tools 44. На живом железе не
  проверялось. [local pytest + parity, 2026-08-28]


## Ночь 28 августа 2026

Диспетчер задач (ADR-0016), Диспетчер устройств (ADR-0017), пути записи для сети/звука/Bluetooth/
питания (ADR-0018), терминал (ADR-0019), Writer частично (ADR-0020, движка в песочнице нет),
ввод в ячейку в Sheets, Slides на живом движке Impress (ADR-0022). Гейты: shell 441 passed +
1 skipped, tools 44, sheets 15, slides 15, writer 9 + 6 skipped, соответствие Windows 11 41/41,
семь эталонных кадров отличаются только часами. Полный разбор — в `NIGHTLY_REPORT.md`.
[замерено в песочнице, 2026-08-28]
