# Changelog

All notable changes to Zaldros OS. Nothing here is a claim that a component has been booted or
benchmarked unless it says so explicitly (spec PART 1 §15).

## [Unreleased]

### Fixed
- Windows are kept inside the work area, so nothing hangs off the edge of a 1280x800 screen.
- The tray keyboard badge shows РУС/ENG instead of "(UN" when no keymap is configured.
- UI font: the vendored Selawik has no Cyrillic, so the Russian interface was silently rendered in
  DejaVu Sans on every ISO. Replaced with PT Sans (OFL 1.1), chosen by measuring against the
  Windows 11 reference capture, installed system-wide with a fontconfig alias, and guarded by
  `tests/test_ui_font.py` (ADR-0011).

### Added
- Task Manager (Ctrl+Shift+Esc): real processes, CPU/memory/disk/network/uptime, GPU where the
  driver reports load, autostart entries, end task, search and sorting — all read from /proc and
  sysfs, with unknown values shown as a dash and no sampling at all while the window is closed
  (ADR-0016).
- Device Manager: the hardware tree read from sysfs, DMI and procfs — PCI, USB, disks, network,
  displays, cameras, input devices, sound cards, printers — with unbound drivers marked and every
  empty category carrying the reason it is empty (ADR-0017).
- Connectivity write paths: joining a Wi-Fi network with a password, VPN profiles on and off, DNS
  and proxy readings, Bluetooth pairing and removal, per-application volume, recording device
  selection and power profiles (ADR-0018).
- Zaldros Terminal: a real pty with our own xterm parser — tabs, split panes, shell profiles,
  Campbell colours, 256-colour and truecolour, the alternate screen, and Windows Terminal's
  shortcuts (ADR-0019).
- Zaldros Writer: a Word-shaped window on the LibreOffice Writer engine — paragraphs, real
  paragraph styles, tables, images, DOCX/ODT/RTF, PDF export and the engine's own pagination
  (ADR-0020).
- A Windows 11-style Alt+Tab switcher of our own (`system/theme/tabbox/zaldros`); the stock KWin
  layout needs the Plasma QML stack and silently did nothing in a Zaldros session.
- Windows 11 widget style for QWidget applications: the `Windows-modern` Kvantum theme (GPL-3)
  plus the `qt6-style-kvantum` engine, so Dolphin and Konsole stop rendering in Breeze.
- Windows 11 window decorations: the Aurorae themes from the "windows-eleven" Plasma global themes
  (GPL-3, zayronXIO) are vendored and selected in `kwinrc`, replacing Breeze title bars on every
  non-shell window; `kwin-style-aurorae` added to the ISO base set.
- Icon coverage: the Windows-Eleven icon theme (~29 700 names, GPL-3) ships as the fallback parent
  of the Zaldros icon theme.
- `docs/PLASMA_THEME_AUDIT.md` — component-by-component audit of both Plasma global themes with
  USE/ADAPT/REFERENCE verdicts, and `tools/visual/kns_audit.py` which resolves their KNewStuff
  dependencies through the OCS API.
- `tools/visual/font_match.py` — ranks candidate UI fonts against real Segoe UI text cropped from
  the reference capture.
- Full specification PARTS 1–5 preserved in `spec/`.
- Combined-spec audit (`docs/SPEC_AUDIT.md`): 6 contradictions resolved, 8 gaps, 5 risks, 7 open questions.
- Architecture set: base distribution, compositor/toolkit, system apps, compatibility/hardware/security,
  performance, security, testing, risks, roadmap (renumbered to the spec's phases 0–14).
- Windows → Zaldros feature matrix (`docs/architecture/FEATURE_MATRIX.md`).
- `tools/zaldros-sysprobe` 0.1.0 — service/dependency/resource map.
- `tools/zaldros-hwinfo` 0.1.0 — real hardware inventory from `/proc` and `/sys`.
- `tools/zaldros-compat` 0.1.0 — compatibility registries with a CI gate rejecting unevidenced claims.
- `tools/zaldros-bench` 0.1.0 — BASELINE → CHANGE → BENCHMARK → COMPARE → ACCEPT/REVERT harness.
- `build/Containerfile.base`, `build/Containerfile.desktop` — **written, never built** (no build host).

### Known state
- No Zaldros image has been built or booted. Zero hardware evidence records. Zero performance baselines.
