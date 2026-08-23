# Worklog

## 2026-08-23 — first ISOs actually built (run #11, d9dff44)

- `apt-update`, `apt-install`, `theme` all exit 0 in all three variants; xorriso wrote
  `zaldros-full.iso` (3.0G), `zaldros-services.iso` (2.9G), `zaldros-legacy.iso` (2.7G).
- The job still reported `failure`: the *Diagnostics summary* step failed (root-owned
  `build-debug-*` written under sudo), which skipped the ISO artifact upload and the boot job.
- Fix (minimal): `continue-on-error: true` on both diagnostics steps + `chown` of the debug dir,
  and `if: always()` on the ISO artifact upload. Diagnostics must never fail the build job.
- Boot evidence: still NONE. Architecture stays PROPOSED / NOT ACCEPTED.


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

## 2026-08-23 — ISO pipeline: diagnosability before more fixes
- Base change recorded as ADR-0009 (Ubuntu 26.04, **PROPOSED**); ADR-0001 (Fedora bootc) superseded.
  Every doc that promised atomic updates, rollback, read-only `/usr` or SELinux corrected.
- `iso` runs #1–#6: all builds FAIL, boot job never ran. No ISO exists, so no metrics exist.
- Root causes found and fixed so far: `plasma-workspace-wayland` is a Plasma 5 name that does not
  exist in 26.04; the runner's debootstrap has no script for `resolute` (now bootstrapping from the
  official Ubuntu base tarball instead).
- Build script now emits a full diagnostic set per variant on every run — step exit codes, apt logs,
  installed packages, sources, chroot DNS/arch/os-release, `df`/`free`/`mount`/`uname`, and 200-line
  tails — uploaded as `build-debug-{variant}` and echoed into the run summary. No more guessing.

## 2026-08-23 — run #14: pipeline works, boot still FAIL 9/9 (empty serial log)
- Evidence: run 32665317028. Builds 3/3 PASS, all 9 boot jobs ran QEMU for the full 900 s
  timeout, artifacts + screenshots + serial logs published to `ci-logs-boot-*` branches.
- `zaldros-full-low.serial.log` is **0 bytes**; screenshot at 120 s is a black screen with a
  firmware cursor. So the kernel never started — the failure is at firmware/GRUB stage.
- Build log shows `grub-mkrescue` writing only the i386-pc `boot_hybrid.img` system area; no
  proof an EFI El Torito image was produced. Not yet a root cause — evidence is missing.
- Diagnostics added instead of guessing: GRUB now speaks to ttyS0 (`serial`/`terminal_output`)
  and echoes each stage, `quiet` removed, `console=tty0 console=ttyS0`; build prints
  `xorriso -report_el_torito` and the `/EFI` listing; boot-test takes an early 25 s screenshot.
- `report.py`: stopped parsing `-host.json`/`.ui-guest.json` as results, and now exits 1 when
  any boot is not PASS, so a green CI job can no longer mean "did not boot".
- Boot: NOT TESTED. Architecture: PROPOSED.

## 2026-08-23 — run #12: builds PASS 3/3, boot FAIL 9/9 (root cause found)
- Evidence: run 32664345534. All three ISOs built (full ~3.19 GB artifact). Every boot job died
  19 ms into `boot-test.sh` with exit 2 and **no output**.
- Root cause (read from the actual log, not guessed): `OVMF="$(ls A B 2>/dev/null | head -1)"`.
  With `set -euo pipefail` the failing `ls` aborted the script *before* the `[ -n "$OVMF" ]` check,
  so the intended `BLOCKED — ENVIRONMENT LIMITATION` message never printed.
- Secondary failure: with `results/` empty the publish step failed on "nothing to commit".
- Fixes: glob-based OVMF discovery + `find` fallback + directory listing on failure;
  EXIT trap writes `<name>.error.txt`; publish step uses `git commit --allow-empty`.
- Boot status: still NOT TESTED. QEMU never started in run #12.

## 2026-08-23 — Owner decisions
- ADR-0005: name **Zaldros OS**, license GPL-3.0-or-later, Russian default + first-class English,
  disk encryption opt-in. Base-distribution decision reopened toward Ubuntu LTS + HWE, to be settled
  by a build test rather than opinion.

## 2026-08-23 — PART 5 integration
- Combined-spec audit, feature matrix, `zaldros-bench` harness, full §14 document set.

## 2026-08-23 — PARTS 1–4
- Phase 0 architecture, ADR-0001…0004, `zaldros-sysprobe`, `zaldros-hwinfo`, `zaldros-compat`,
  Containerfiles (never built).
