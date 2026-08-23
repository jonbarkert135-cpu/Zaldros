# Worklog

Newest first. Each entry states what was *run*, not only what was written.

## 2026-08-23 — Themes installed, not coded
- `system/theme/fetch-sources.sh` + `install-visual-theme.sh`: the ISO now installs Win11-gtk-theme,
  Win11-icon-theme and Fluent cursors through **their own installers** and forces them as defaults
  (kdeglobals, GTK settings, GNOME schema override, kwinrc, `/etc/zaldros/visual.conf`).
- KWin config carries the Windows 11 geometry: blur + contrast effects, borderless maximised
  windows, Aurorae decoration — configuration, not shell code.
- The shell reads `/etc/zaldros/visual.conf` and uses the **installed** icon theme; the vendored
  subset is only a fallback for build containers.
- Desktop icons and the Explorer sidebar now use Win11-icon-theme SVGs instead of drawn glyphs.
- Ran it: 44 shell + 44 tool tests green; evidence renders regenerated.

## 2026-08-23 — Open-source visual foundation integration
- The sandbox got network access, so the research was done **on the real repositories**: cloned and
  read Win11-gtk-theme, Win11-icon-theme and AnduinOS, plus ~15 further projects.
- **Vendored and wired in**: Selawik (Microsoft, OFL 1.1) and 26 Fluent UI System Icons (Microsoft,
  MIT). The shell now renders Microsoft's own font and icons — legally.
- Application icons now come from the host icon theme by freedesktop name, with a lettered fallback.
- `LICENSE` finally contains the full GPL-3.0 text (fetched from gnu.org).
- Adopted the 75 ms hover timing measured in Win11-gtk-theme; kept our own colours and radii after
  comparing them (that theme is Material underneath).
- Fixed: context menu was translucent enough to read the window behind it.
- Ran it: 40 shell tests + 44 tool tests green; six evidence renders regenerated, plus before/after.
- New docs: `VISUAL_FOUNDATION_RESEARCH.md`, `VISUAL_LICENSE_AUDIT.md`, `ZALDROS_DESIGN_SYSTEM.md`,
  `VISUAL_COMPONENT_MATRIX.md`.

## 2026-08-23 — Visual foundation
- Licence-audited the open-source Windows-like field into `docs/VISUAL_THIRD_PARTY.md`; found the
  legally clean route: Fluent UI System Icons (MIT) + Selawik (OFL), both from Microsoft.
- Rebuilt the shell around a full design-token system with dark **and** light themes.
- Added: system tray, quick settings flyout, context menus, window decorations, keyboard navigation.
- Added real backends: `.desktop` discovery + launching, and sysfs/wpctl readouts for battery,
  brightness, network, volume, Bluetooth.
- Ran it: 76 tests green (44 tools + 32 shell), six evidence renders in `docs/evidence/`.
- Adopted the **ponytail** skill (lazy-senior-dev review): replaced the hand-written .desktop parser
  with stdlib `configparser`.
- Scores and honest limits: `docs/VISUAL_SCORE.md`.

## 2026-08-23 — Reality audit + first desktop vertical slice
- Audited every component against REAL/PROTOTYPE/BACKEND ONLY/DOCUMENTATION ONLY/MISSING
  (`docs/REALITY_AUDIT.md`). Verdict: the project was documentation + backend only. Owner was right.
- Built the first UI: `shell/zaldros-shell` — Qt 6/QML taskbar and Start menu, PySide6 6.11.2.
- Ran it: rendered offscreen to `docs/evidence/shell-desktop-ru.png`, `shell-start-ru.png`,
  `shell-desktop-en.png`. 9 shell tests (backend + render/visual) pass; 44 tool tests still pass.
- Real data in the UI: locale-formatted system clock, running-app underline from `/proc`, memory
  pressure in the Start footer (shows `—` when unmeasurable).
- Wrote `docs/WINDOWS_ZALDROS_PARITY.md` (0 COMPLETE / 3 PARTIAL / 3 PROTOTYPE / 2 BACKEND ONLY /
  21 MISSING) and `docs/FEATURE_RESEARCH.md`.
- Still blocked: no container build, no VM boot, no hardware or performance evidence.

## 2026-08-23 — Owner decisions
- ADR-0005: name **Zaldros OS**, license GPL-3.0-or-later, Russian default + first-class English,
  disk encryption opt-in. Base-distribution decision reopened toward Ubuntu LTS + HWE, to be settled
  by a build test rather than opinion.

## 2026-08-23 — PART 5 integration
- Combined-spec audit, feature matrix, `zaldros-bench` harness, full §14 document set.

## 2026-08-23 — PARTS 1–4
- Phase 0 architecture, ADR-0001…0004, `zaldros-sysprobe`, `zaldros-hwinfo`, `zaldros-compat`,
  Containerfiles (never built).
