# Worklog

## 2026-08-26 — ADR-0010: of the theme packs, only the cursors ship

The maintainer asked why Zaldros exists when Linuxfx/WindowsFX (now Winux) already does this, and
whether it could be copied one to one. It cannot: that project is proprietary and paid, its own
components are unpublished, and its Windows look is — by its maintainer's own description — Ubuntu
plus open-source theme packs on KDE Plasma. So there was nothing unique to copy, only the same GPL-3
packs anyone can take. His decision: **take the cursors, draw everything else ourselves.**

Implemented in this cycle:

* `fetch-sources.sh` sparse-clones one project, `vinceliuice/Fluent-icon-theme`, `cursors/` only.
  Its prebuilt `dist` / `dist-dark` are copied unmodified (111 shapes), licence installed to
  `/usr/share/doc/zaldros/licenses/`.
* The pointer is now actually applied, which it never was: `/usr/share/icons/default/index.theme`
  (Xcursor ignores everything else), `/etc/xdg/kcminputrc` for KDE, GTK settings, the GNOME schema
  override, `/etc/profile.d` and an explicit `XCURSOR_THEME` export in `zaldros-session` — systemd
  starts it as a plain `/bin/sh`, so profile.d alone would have changed nothing. This is the
  `no cursor theme` line that has been in the session log since run #17.
* `Win11-gtk-theme` and `Win11-icon-theme` are out of the image. The system icon theme `Zaldros` is
  generated from `assets/icons/{apps,places,fluent}` in freedesktop layout, so Qt, GTK and the shell
  resolve the same names. GTK apps get stock Adwaita plus our colour tokens — recorded as colour
  parity only, not as Windows parity.
* `selftest.py` reports a `visual_layer` block (cursor theme installed, shape count, default alias,
  `XCURSOR_THEME`, icon theme present) so a missing theme shows up in CI, not only in a log tail.
* `tests/test_visual_layer.py` fails the build if a theme pack reappears in the build scripts or if
  `visual.conf` names a cursor theme nothing installs.

Still borrowed after this: the 17 app and 9 place SVGs vendored in `assets/icons/` are upstream
GPL-3 artwork. Replacing them with our own is in `TODO.md`; window titlebars stay borderless Breeze
until our own Aurorae theme exists, and that is named as a placeholder in the component matrix.

## 2026-08-26 — run #27: Windows 11 visual parity, cycle 1

Goal for this cycle, set by the maintainer: pixel-level Windows 11 parity for the shell. Kernel,
base and KWin untouched; performance work restricted to the backend.

**Reference is now numeric.** `tools/visual/measure_reference.py` measures real Windows 11 captures
(the committed 1920x1280 Start capture plus private maintainer screenshots that were measured and
then deliberately not committed) and writes logical values to `system/theme/win11-reference.json`:
taskbar 48 / icon 24 / button pitch 44, Start 640x726 with 32 padding and a 576x38 search field,
6 x 96x84 pin cells, 64 footer, 12 gap above the taskbar, Explorer 40/48/48 bars with a 190 sidebar
on #191919, Settings rail 320, flyouts 360 at 12 from the edge, menu items 32.

**Checked, not claimed.** `tools/visual/parity.py` renders seven states offscreen, reads the live
geometry of every named component back out of the scene graph and compares it against those
numbers: **29 of 29 checks match**. `tests/test_visual_parity.py` runs the same comparison in CI,
so drift fails the build. Evidence: `docs/visual/current/` (frames, per-component crops,
`parity-report.json`).

**Reworked to the measurements:** taskbar (centred group at 44 px pitch, search field, task view,
window buttons, tray with layout badge, grouped network/volume/battery pill, two-line clock,
notification button, show-desktop strip); window chrome (32 px Mica title bar, 46x32 captions with
the #c42b1c close hover, layered shadow, real drag/minimise/maximise/close, tabbed title bar for
Explorer); Start (measured grid, real recent files instead of an empty Recommended panel); search
flyout over installed applications; quick settings; notification centre with a real month calendar;
context menu.

**Explorer and Settings are applications now, not mockups.** Explorer lists and navigates this
machine's real directories (`zaldros_shell/files.py`) with breadcrumbs, back/forward/up, command
bar, column header, status count and honest empty/error states. Settings shows 11 pages of real
readings from `zaldros_shell/hostinfo.py` (device, OS, kernel, CPU, RAM, disk, uptime, session,
time zone); anything the system cannot report renders as a dash. A test fails the build if
placeholder copy reappears in either application.

Also: 55 real Fluent UI System Icons (Microsoft, MIT) vendored for the new controls, and the tray
keyboard badge now reads the session layout instead of printing whatever `LANG` contains.

## 2026-08-23 — run #17 (0d364d1): DESKTOP UP on all 9 combinations, boot verdict still FAIL
- Evidence: run 32669197023, all 12 jobs green; per-job JSON/serial/screenshots on `ci-logs-boot-*`.
- **First real desktop.** The systemd autologin session works: `kwin_wayland` running,
  `/run/user/1000/wayland-0` present, shell alive, on full/services/legacy x low/mid/modern.
- Measured (idle, in QEMU/llvmpipe — architecture comparison only, NOT hardware evidence):

  | variant | procs | RAM used (low/mid/modern MiB) | KWin RSS | shell RSS |
  | --- | --- | --- | --- | --- |
  | full (plasmashell) | 39 | 875 / 951 / 1043 | 245.7 | plasmashell 394.9 |
  | services (KWin + Zaldros shell) | 22 | 461 / 482 / 542 | 188.9 | python3 33.5 |
  | legacy (LayerShell) | 22 | 467 / 477 / 533 | 181.0 | python3 ~33 |

- Boot verdict `FAIL` everywhere, on two real checks — no verdict softened:
  1. `systemd_state = starting`: the self-test sampled `is-system-running` before jobs settled,
     and `casper-md5check.service` (live-ISO checksum) fails on our generated image.
     Fix: mask `casper-md5check`, and wait for the state to settle before reporting it.
  2. `app_launch` FAIL on services/legacy (konsole exits at once) and every KWin window step
     FAIL on all variants (`windows() == []`). ROOT CAUSE: the self-test/UI-test units run as
     root with no session bus, and `qdbus6` is not even installed — so nothing could ever reach
     `org.kde.KWin`. Full Plasma passed the host-side Start/taskbar checks because plasmashell
     brings its own bus. Fix: install `dbus-user-session`, export
     `DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus` to the session and to the tests,
     and call KWin through `dbus-send` (ships with dbus) instead of qdbus6.
- Host-side QMP input (full variant): Start open PASS 1.5 s, Start close PASS, taskbar PASS,
  Alt+Tab FAIL (screen unchanged — only one window existed). services/legacy: all FAIL.
- Architecture stays **NOT ACCEPTED**: no combination has a green boot verdict yet.


## 2026-08-23 — run #15: first real boot — kernel + systemd PASS, desktop FAIL
- Evidence: run 32666821061 (0a210fe). Builds 3/3 PASS. Serial logs on the `ci-logs-boot-*` branches.
- **The system boots.** `ZALDROS-SELFTEST {...}` reached ttyS0 from inside the guest:
  kernel `7.0.0-30-generic`, systemd `starting`, graphical.target reached, 16 processes, 354 MiB used.
- Three real failures, each read from the log rather than guessed:
  1. `boot-test.sh` reported FAIL although the marker was present — getty printed
     `ubuntu login: ` on the same line and the grep was anchored with `^`. Fixed: `grep -o`.
  2. Every job burned the full 15 min timeout: casper's shutdown asks
     "Please remove the installation medium, then press ENTER" and loops on `cdrom.mount`.
     Fixed: `noprompt` on the kernel command line.
  3. No compositor: `kwin: false`, `wayland_socket: []`, `konsole` did not start, only sddm alive.
     Likely cause: autologin pointed at a `zaldros` user, but casper creates its own live user
     `ubuntu` (uid 1000). Fixed: autologin as `ubuntu` into `zaldros.desktop`, extra user dropped.
     Not yet proven — the next run adds the evidence for it (sddm journal, `/run/user/*`,
     available sessions) instead of asserting it.
- `selftest.py` now waits up to 90 s for `kwin_wayland` and attaches the session diagnostics.
- `casper-md5check.service` fails on every boot (cosmetic for CI, will be disabled later).
- Boot: PARTIAL. Architecture: still PROPOSED — no variant produced a desktop, nothing to compare.

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

## 2026-08-23 — Run #16: first honest desktop failure, root cause found
- All 12 CI jobs green, but the evidence says otherwise: `kwin=false`, no Wayland socket,
  `konsole` did not start, every UI step FAIL, 12-15 processes, 355-444 MiB used.
- Root cause (read from `sddm_journal`, not guessed): sddm never applied the autologin
  config, fell back to its X greeter, and this image ships no Xorg ->
  "Failed to start display server process. Attempt 1 ... failed". Nothing started a session.
- Fixes: (1) sddm dropped entirely; `zaldros-session.service` autologins user `ubuntu` on
  tty1 via PAM and execs the variant session directly — fewer processes, ~25 MiB less RSS.
  (2) self-test no longer counts its own `python3` as "the shell" (pgrep zaldros_shell) and
  launches the test app as the session user with XDG_RUNTIME_DIR/WAYLAND_DISPLAY.
  (3) `boot=PASS` is now computed from kernel+systemd+wayland+kwin+shell+app_launch;
  a self-test marker alone is no longer a PASS.
- Architecture: still NOT ACCEPTED. No variant has produced a desktop yet.

## 2026-08-23 — Owner decisions
- ADR-0005: name **Zaldros OS**, license GPL-3.0-or-later, Russian default + first-class English,
  disk encryption opt-in. Base-distribution decision reopened toward Ubuntu LTS + HWE, to be settled
  by a build test rather than opinion.

## 2026-08-23 — PART 5 integration
- Combined-spec audit, feature matrix, `zaldros-bench` harness, full §14 document set.

## 2026-08-23 — PARTS 1–4
- Phase 0 architecture, ADR-0001…0004, `zaldros-sysprobe`, `zaldros-hwinfo`, `zaldros-compat`,
  Containerfiles (never built).

## Run #18 — first full green pipeline, first real boot evidence (2026-08-23)

All 12 jobs succeeded (build full/services/legacy + 9 boot jobs). Evidence, not conclusions:

| variant | profile | boot | RAM used | procs | kwin | shell | app launch |
|---|---|---|---|---|---|---|---|
| full | low/mid/modern | FAIL (systemd) | 854/897/966 MiB | 39 | PASS | plasmashell PASS | konsole PASS |
| services | low/mid/modern | FAIL (systemd, app_launch) | 454/484/537 MiB | 22 | PASS | zaldros_shell PASS | FAIL |
| legacy | low/mid/modern | FAIL (systemd, app_launch) | 452/482/547 MiB | 22 | PASS | zaldros_shell PASS | FAIL |

Three root causes read off the actual logs (no guessing):

1. `app_launch` FAIL on services/legacy — konsole aborts with
   `qt.qpa.wayland: No shell integration named "xdg-shell" found` (exit 134). The Qt Wayland
   shell-integration plugins come with `qt6-wayland`, which only full pulled in via plasma-desktop.
   Fix: `qt6-wayland` added to the base package set.
2. Every window UI step FAIL — `dbus-send --session` timed out: the UI test ran as root against
   the ubuntu user's bus socket, and the bus refuses a uid mismatch. Fix: the unit now runs the
   UI test through `runuser -u ubuntu`.
3. `systemd` check FAIL with **zero failed units** — `is-system-running` stays `starting` while a
   job of the initial transaction is running, and that job is the self-test itself. Fix: the
   self-test now records `systemctl list-jobs`, and `starting` passes only when the outstanding
   jobs are its own units and nothing failed.

Host-side QMP input (full variant): Start open PASS 1.5 s, Start close PASS, taskbar PASS,
Alt+Tab FAIL. services/legacy host input all FAIL — expected fallout of (1): no client windows.

Architecture decision stays **PROPOSED**. RAM/process deltas (full ~854 MiB / 39 procs vs
~453 MiB / 22 procs) are recorded but are not a verdict until a boot PASS with working UI.

## Run #18 (b17846d) — first green boot, and the black screen behind it

12/12 CI jobs green. All 9 variant x profile combinations passed the guest self-test:
kernel 7.0.0-30-generic, systemd, Wayland, KWin, session unit, konsole launch 2.0 s, 0 failed units.
Full table and verdicts: `docs/state/iteration-reports/0009-first-green-boot.md`.

But the screenshots disagree with the JSON: `services` and `legacy` produce a *fully black* frame.
Root cause read off the code, not guessed:

1. `zaldros-session` ran `python3 -m zaldros_shell` with no subcommand. The CLI declares
   `add_subparsers(..., required=True)`, so argparse exited 2 the instant the session started —
   the shell never drew anything. Fix: `... zaldros_shell run`.
2. The self-test still reported `shell: true` because `pgrep -f zaldros_shell` matched
   *kwin_wayland's own command line*. Fix: match `^python3 -m zaldros_shell`, and capture the
   session journal into the artifact so the next failure names itself.
3. The shell QML imports `QtQuick.Controls`, which only the `legacy` package set installed.
   Moved `qml6-module-qtquick-controls` into the base set.

Architecture verdict stays open: `full` ACCEPT (provisional, only visible desktop),
`services`/`legacy` MODIFY — half the RAM (452 vs 883 MiB, 22 vs 39 processes) but no visuals yet.

## Run #19 candidate (2026-08-24) — black screen: second root cause, and real boot time

Written and unit-tested locally (44 shell tests + shell render green); CI evidence pending.

1. **Assets vanished inside the ISO.** `app.py` resolved the asset tree as `parents[3]/assets`,
   which is correct in the repo checkout but lands on `/assets` when the shell is installed flat
   at `/opt/zaldros`. So in every ISO the shell ran with no wallpaper, no Selawik font and no
   Fluent icons — the other half of the services/legacy black frame, next to the argparse exit.
   Fix: `_assets_dir()` tries `$ZALDROS_ASSETS`, the repo layout, the flat layout and
   `/opt/zaldros/assets`, and only accepts a directory that actually contains `wallpaper/`.
2. **The shell opened a 1600x1000 window on a 1280x800 screen.** `run()` now sizes the view to the
   primary screen, sets `SizeRootObjectToView` and calls `showFullScreen()`.
3. **Boot time is measured, not estimated.** The self-test reports `boot_time`:
   `uptime_at_selftest_s` from `/proc/uptime` plus `systemd-analyze time` (kernel/userspace split)
   when available — `null` when it is not, never a guessed number. `wall_seconds` stays the
   harness ceiling and is not a boot time.

## Run #20 candidate (2026-08-24)
- CI for c4c7f3d: iso 32672535930 + CI 32672536000 both green. Guest verdicts are now honest:
  full/low|mid|modern boot=PASS (but that session is startplasma-wayland, i.e. stock Plasma, not our
  shell); services/* and legacy/* boot=FAIL with failed_checks=["shell"] — screenshots 282 B (black).
- Root cause work: `zaldros-session.service` journal holds only the two PAM lines, so the shell's own
  stderr was never captured. Session script now tees everything to /var/log/zaldros-session.log
  (with `set -x`) and reports the child's exit status; the self-test reads that file back as
  `session_log` (None when absent — never a guess).
- Fixed a real data bug: `selftest.py` had two `"boot_time"` keys; the second
  (`systemd-analyze time`, empty while systemd is still "starting") silently overwrote the measured
  value from `boot_seconds()`. That is why every run #19 report showed boot_time "". Removed.

## Run #21 candidate (2026-08-24)
- CI b93c4a7 green; boot logs показали причину падения сессии: `zaldros-session.service` exit
  status=2 в ту же секунду. Виновник — сам диагностический редирект: `/var/log` не доступен на
  запись пользователю ubuntu, поэтому `exec >>/var/log/zaldros-session.log` завершал скрипт до
  запуска kwin. Поле `session_log` пришло `null` (tail_file честно вернул None, не догадку).
- Исправлено: лог сессии пишется в `/tmp/zaldros-session.log`, selftest читает оттуда же.
- Открыто: `full` всё ещё стартует startplasma-wayland (отклонение от спеки), Alt+Tab host FAIL,
  boot_time: systemd-analyze пуст (systemd ещё "starting"), меряем uptime_at_selftest_s.

## Run #22 (2026-08-24)
- Root cause of the black screen in services/legacy found from /tmp/zaldros-session.log:
  `ModuleNotFoundError: No module named 'PySide6.QtSvg'` — the ISO installed only
  python3-pyside6.qtquick. kwin_wayland itself started fine.
- Fix: add python3-pyside6.qtsvg to the ISO package list.
- Guard: tests/test_iso_packages.py asserts every `from PySide6.X import` in the shell
  has a matching python3-pyside6.x package in build-iso.sh.
- full variant now runs /usr/local/bin/zaldros-session (own shell) instead of
  startplasma-wayland, as the spec requires.

## Run #23 (2026-08-24)
- CI 6358bdd: все 9 образов зелёные, kwin=true во всех, но shell=false. Из
  /tmp/zaldros-session.log: `zaldros-shell: error: argument command: invalid choice: 'run;'`.
- Причина: kwin_wayland заново разбивает аргумент приложения по пробелам, поэтому
  `sh -c 'python3 -m zaldros_shell run; ...'` пришёл как отдельные слова.
- Фикс: отдельный однофайловый враппер /usr/local/bin/zaldros-shell-run, kwin получает один путь.

## Run #24 (60e478b) — the wrapper worked, the shell still exits (2026-08-24)

iso run 32675722125: 12/12 jobs green, and green again means nothing. All nine
`variant x profile` guest verdicts are `boot=FAIL, failed_checks=["shell"]`.

Confirmed working in every combination: kernel 7.0.0-30-generic, systemd with 0 failed units,
`/run/user/1000/wayland-0`, `kwin_wayland`, the autologin session unit, konsole launch 2.0 s.
The single-file wrapper from run #23 did its job: `/tmp/zaldros-session.log` now shows
`exec kwin_wayland --xwayland -- /usr/local/bin/zaldros-shell-run` with no argument splitting.

Root cause, read off the session log, not guessed:

```
FileNotFoundError: [Errno 2] No such file or directory: '/opt/zaldros/data/pinned.json'
zaldros-shell exited 1
```

`build/iso/build-iso.sh` copied `zaldros_shell/`, `qml/`, `assets/` and `theme/` into
/opt/zaldros and never copied `shell/zaldros-shell/data/`. The shell reads its pinned
application list at import time, so it died before drawing a pixel — the same class of bug as
the run #19 asset-path miss, and again invisible to a test suite that imports the shell from the
repository checkout.

Fixes in this commit:

1. `build-iso.sh` copies `data/` into the image.
2. `backend.py` resolves the data tree the way `app.py` resolves assets (`$ZALDROS_DATA`, repo
   layout, flat layout) and keeps a stable path when nothing is found, so a missing file still
   fails loudly.
3. `tests/test_flat_layout.py` — the real guard: it parses the `cp` commands out of
   `build-iso.sh`, stages exactly that tree in a temp directory and renders one frame from it in
   a subprocess with `PYTHONPATH` pointing only at the staged tree. Removing the `data/` copy
   makes it fail in under a second instead of after a 13-minute ISO run (verified both ways).

Also recorded from run #24: boot time is finally a measured number — `uptime_at_selftest_s`
21.6–24.3 s across the nine combinations (`systemd-analyze` still returns nothing while systemd
reports `starting`). RAM 440–558 MiB at 21–24 processes, but that is a KWin-only session with no
shell, so it is not architecture evidence.

Known noise in the same log, not yet addressed: KWin cannot find the `ZaldrosDark` colour scheme
(falls back to BreezeLight), no `default` cursor theme, no `applications.menu`, and the
`org.kde.kwin.aurorae.v2` decoration plugin is missing. None of these stop the session.

## Run #25 — first honest BOOT PASS, and the UI test caught lying

iso run 32991329542: 9/9 combinations `boot=PASS, failed_checks=[]`. The shell renders — the
QMP screenshots show the wallpaper, desktop icons, the taskbar, the Start group and both window
mockups on all three variants. Shipping `data/` was the last thing between the image and a
working session.

Measured in this run (guest self-test, not estimated):

| combination | boot | uptime at self-test | RAM used | processes |
|---|---|---|---|---|
| full / low | PASS | 23.4 s | 655 MiB | 26 |
| full / mid | PASS | 24.0 s | 680 MiB | 26 |
| full / modern | PASS | 24.3 s | 738 MiB | 26 |
| services / low | PASS | 23.3 s | 606 MiB | 23 |
| services / mid | PASS | 23.3 s | 632 MiB | 23 |
| services / modern | PASS | 24.4 s | 687 MiB | 23 |
| legacy / low | PASS | 22.8 s | 606 MiB | 23 |
| legacy / mid | PASS | 21.3 s | 633 MiB | 23 |
| legacy / modern | PASS | 21.9 s | 685 MiB | 23 |

Largest resident processes are the shell (python3, ~319 MiB) and kwin_wayland (~270 MiB).

Every UI step still reported FAIL, and three separate reasons were found, none of them a shell
defect:

1. **The window query never read anything.** `uitest.py` looked for KWin's `console.info` output
   in the journal, but the session unit redirects its own output to `/tmp/zaldros-session.log`
   (run #20). `windows()` therefore always returned `[]`, so `desktop_ready` said "no windows
   yet", `app_launch_explorer` timed out after 30 s and move/minimize/restore all failed against
   a session that had the windows open on screen.
2. **KWin refuses to run the same script path twice.** Every poll wrote `/tmp/zaldros-windows.js`
   and called `loadScript` on it, so even a fixed log source would only have worked once.
3. **The host driver clicked an empty spot and pressed keys nobody handled.** The taskbar group
   is centred and its width depends on the pinned applications, so the hard-coded `(24, h-24)`
   click landed on bare taskbar. Meta and Alt+Tab reached the shell and did nothing, because
   with bare `kwin_wayland` and no plasmashell there is no component in the session that owns
   those keys.

Fixes in this commit:

* `Shell.qml` handles the shell keys itself: Meta toggles Start, Escape closes Start, quick
  settings and context menus, and an `Alt+Tab` shortcut moves focus between the two window
  surfaces (Tab alone is eaten by Qt's focus chain, so a key handler is not enough — a real
  `Shortcut` is). Measured offscreen: Alt+Tab changes 8.6 % of the pixels.
* `app.py` publishes the on-screen hit boxes (`/tmp/zaldros-ui-geometry.json`, Start button
  centre in view coordinates) two seconds after the first frame; `selftest.py` prints them on
  serial as `ZALDROS-GEOMETRY {...}` and `ui-drive.py` clicks that point instead of a guess. If
  the geometry is missing the step reports BLOCKED with the reason — no guessed coordinates.
* `uitest.py` reads `/tmp/zaldros-session.log` first and uses a fresh script path per query.
* `ui-drive.py` compares frames by the fraction of differing bytes (threshold 0.2 %) instead of
  by mean brightness, which hid a menu that opened and closed again.
* `tests/test_input.py` presses Meta, Escape and Alt+Tab on a real `QQuickView` and checks the
  published hit box sits inside the 48 px taskbar band.

Still open after this run: the missing `ZaldrosDark` colour scheme, no `default` cursor theme, no
`applications.menu`, the absent `org.kde.kwin.aurorae.v2` decoration plugin, and the icon
provider failing for `soffice`, `zutty` and `gvim` in the pinned grid.

## Run #27 — visual parity cycle 1 measured, and why Alt+Tab was dead

Boot: 9/9 profiles PASS with the rebuilt shell (`shell=true`, `kwin=true`, no failed units;
608-745 MiB used, 21-24 s to self-test). Host UI: `start_open`, `start_close` and
`taskbar_response` PASS; `alt_tab` FAIL with `changed_fraction` exactly 0.0 in all nine.

Zero change is the tell: the key never reached anything. The shell's own `Alt+Tab` `Shortcut`
only fires while the shell surface has focus, and by that step Dolphin owns it. The switcher is
KWin's job — but KWin does not grab keys itself. It registers "Walk Through Windows" with the
global accelerator daemon, and that daemon (`kglobalacceld`) is only a *recommend* of
`kwin-wayland`, so `--no-install-recommends` left it out of every image we have ever built. With
no daemon, the registration is dropped without an error and Alt+Tab is dead for the session.

Fix in this commit, three parts because all three must hold:

* `build-iso.sh` installs `kglobalacceld`, falling back to `kglobalaccel-bin` on KF5 suites, and
  keeps building if neither exists rather than failing the ISO over a shortcut.
* `zaldros-session` starts the daemon before `exec kwin_wayland`, so the registration has
  somewhere to go.
* `install-visual-theme.sh` writes `[TabBox]` in `/etc/xdg/kwinrc` (thumbnail grid, the closest
  KWin switcher to the Windows 11 layout) and `/etc/xdg/kglobalshortcutsrc` with Alt+Tab,
  Alt+`, Meta+D, Alt+F4 and the Meta+arrow snap bindings.

`tests/test_iso_packages.py::test_alt_tab_is_wired_end_to_end` asserts all three so this cannot
regress quietly. The switcher's own skin is still KWin's, not a Windows 11 one — that is on the
cycle 3 list, together with Explorer file operations and nested Settings pages.

## Run #28 — the taskbar and Settings measured against the second reference set

The maintainer sent a full-width taskbar capture, the keyboard-layout flyout, Quick Settings and
ten Settings pages (all at 125 %). Measured, then deleted: only numbers reached the repository.

Taskbar, from measurement rather than memory:

* the search pill is **220** logical pixels wide, not 200;
* the bar is a flat **#212121** with a 1 px lighter top edge — no wallpaper showing through, so
  the 95 % alpha fill is gone;
* Windows keeps a **handful** of pins on the bar. Ours showed all eighteen, which was the single
  biggest reason the screenshot did not read as Windows. `pinned.json` now marks the six that
  live on the bar; Start still shows the whole set;
* the left end carries a weather widget: 24 px icon at x=20 and two text lines. `weather.py`
  fetches it from Open-Meteo using `/etc/zaldros/weather.conf`; with no config or no network the
  widget says so instead of inventing a temperature.

Settings became a real tree instead of one flat list per category. `settingspages.py` holds the
Windows 11 information architecture — 65 pages, every row either navigating somewhere real or
showing a reading — and `SettingsTree` hands it to QML, which now has a back arrow, nested pages,
section headings ("Зрение", "Слух", "Взаимодействие") and Windows-style switches.

Deliberately dropped, because Raven has no counterpart and a dead row is worse than no row:
activation, OneDrive, Microsoft accounts, subscriptions, payments, order history.
`tests/test_settings_tree.py` fails if any of them comes back, if a row leads to a page that does
not exist, or if a page becomes unreachable from the rail. "Получить помощь" opens this
repository's issue tracker.

Parity: 34/34 (four new taskbar checks). Tests: 67.

## Run #28b — the shortcut daemon was installed but never found, and windows keep their corners

The run #27 fix installed `kglobalacceld` and the session still logged four failed `[ -x ]` tests:
KF6 ships the binary under a multiarch libexec directory, not `/usr/bin`. The build now asks
`dpkg -L` where the binary actually is and writes it to `/etc/zaldros/accel-path`; the session
starts exactly that path and says so in its log when there is none. Guessing paths is what cost
this a whole ISO cycle.

Also from the maintainer's review of the shipped screenshots:

* Settings has **no application icon** in its title bar — a back arrow stands where the icon
  would be, and it walks the nested page stack (`AppWindow.showIcon` / `showBack`).
* Every window keeps its **8 px corners when maximised**. `BorderlessMaximizedWindows` is off in
  `kwinrc` for the same reason.

## Run #28c — the UI font could not write Russian

The maintainer's review of the shipped Settings screenshot: "шрифты в этой панели вообще не те".
He was right, and the cause was not styling.

`assets/fonts/selawik/selawk.ttf` has 383 glyphs and **zero Cyrillic codepoints**. Selawik was
vendored (ADR-0007) for one property — metric compatibility with Segoe UI — and nobody checked
whether it could draw the alphabet the interface is written in. Qt registered it, `Theme.fontFamily`
said "Selawik", and every Russian label was quietly handed to fontconfig's fallback: `fonts-dejavu-core`,
the only font family in the image. So the shell has been rendering in DejaVu Sans since the first
ISO, in every screenshot we ever sent.

Picked the replacement by measurement instead of taste. `tools/visual/font_match.py` crops real
Segoe UI Cyrillic out of `assets/refs/win11_start_reference.png` (a Russian Windows 11 desktop),
renders the same string in each candidate, scales to the reference's ink height and compares
pixels. PT Sans wins both samples — 62.0 % difference on body text against DejaVu's 93.0 %, and
PT Sans Bold lands 31.6 % from Segoe UI Semibold on the "Закрепленные" heading, with a width ratio
of 0.99. It also tracks Segoe metrics best of the field (5.4 % mean advance deviation, identical
x-height and cap height), so the geometry tokens measured for Segoe still hold.

What changed:

* `assets/fonts/pt-sans/` replaces `assets/fonts/selawik/` (SIL OFL 1.1, ParaType, licence shipped).
* `app.load_fonts()` walks the whole font tree and returns a family only if it registered **and**
  reports Cyrillic coverage; otherwise it prints the fallback it really got. `ZALDROS_UI_FONT`
  overrides it for comparisons.
* `install-visual-theme.sh` installs the faces into `/usr/share/fonts/truetype/zaldros`, writes
  `/etc/fonts/conf.d/60-zaldros-ui-font.conf` (sans-serif, system-ui, Segoe UI and Selawik all map
  to PT Sans) and names the family in kdeglobals, GTK 3/4, the GNOME schema override and
  `visual.conf`. KWin decorations, Dolphin and Konsole were drawing in DejaVu too.
* `tests/test_ui_font.py` — five gates: faces plus licence present, Cyrillic covered, every
  character used in the shell sources covered, shell and theme name the same family, font installed
  system-wide. Verified the coverage gate fails on the old Selawik file before committing.

Tests: 116. Parity: 34/34 (unchanged — the geometry tokens were never the problem).

Lesson, same shape as the `kglobalacceld` path guess: a dependency that "is installed" is not a
dependency that *works*. Check the property you actually need — here, that the font can draw the
text — not the property that was convenient to check.

## Run #29 — the Plasma "windows-eleven" themes: what could be borrowed, and what could not

The maintainer sent two Look-and-Feel packages by zayronXIO with a clear instruction: prove that
existing Plasma work cannot be used before writing more visuals ourselves.

First finding: the archives contain almost nothing. A Plasma global theme is configuration — a
panel build script, a `defaults` file, a splash, previews — and every visible asset is a KNewStuff
dependency fetched from kde-look.org (19 products for light, 20 for dark). `tools/visual/kns_audit.py`
resolved all of them through the OCS API; each one was downloaded and opened.

Second finding: the panel script literally builds a plasmashell panel out of plasmoids (OnzeMenu,
icontasks, systemtray, digitalclock). Zaldros replaced plasmashell with its own shell (ADR-0008),
so most of the package cannot execute here at all — not a licensing problem, an architecture one.

Third finding, the useful one: two components need KWin or freedesktop paths only.

* **Aurorae decorations** (p/1977804 light, p/1984455 dark, GPL-3). Aurorae is KWin's SVG
  decoration engine, packaged as `kwin-style-aurorae` — verified in the Ubuntu 26.04 contents
  index rather than guessed, after the `kglobalacceld` lesson. Breeze title bars were the most
  obviously non-Windows thing on any Dolphin window; these are Windows 11 title bars with the
  caption buttons on the right, close 40 px wide, centred title. Both variants are vendored and
  wired through `kwinrc` (`[org.kde.kdecoration2]` is still the config group name in KWin 6, even
  though it loads kdecoration3 plugins).
* **Windows-Eleven icon theme** (p/1977340, GPL-3, ~29 700 files). Our own set is 116 SVGs, so
  every other KDE dialog fell through to an empty hicolor. The pack is now the *parent* of the
  Zaldros theme: our icons win, its icons fill the gaps.

Everything else is REFERENCE ONLY with a written reason, including the Plasma theme SVGs (they only
render inside plasmashell's FrameSvg), OnzeMenu, the plasmoids and the wallpapers. Kvantum is a
candidate for a later cycle: it would restyle Dolphin's widgets and needs no Plasma, but neither
the package nor a Win11 Kvantum theme was in these archives.

Gates: `tests/test_borrowed_theme.py` (6). Tests: 122. Parity: 34/34.

Still open: how the Aurorae title bars actually look has to come from a booted ISO — the offscreen
renderer draws our shell, not KWin decorations.

### Run #29b — why Alt+Tab kept failing, and the colour scheme that was never installed

The ISO for `21e75c0` finished while the audit was running. Two things from its logs:

1. **Alt+Tab: the test was wrong, not (necessarily) the system.** The session log now shows the fix
   from #28b working — `/etc/zaldros/accel-path` resolved, `kglobalacceld` started, then
   `exec kwin_wayland`. Yet `changed_fraction` is still exactly 0.0. The reason is in the driver:
   the host pressed Alt+Tab as its *third* step, seconds after boot, when the fullscreen shell was
   the only toplevel window. KWin shows no switcher for a single window, and QEMU's chord releases
   Alt long before the screenshot — so the frame could not change whatever the shortcut did. The
   step now runs last, after the guest has published its geometry (by which time the in-guest test
   has opened Dolphin), and reports BLOCKED rather than FAIL when no second window exists.
2. **`Could not find color scheme "ZaldrosDark" falling back to BreezeLight`.** `kdeglobals` named a
   scheme that no file provided, so every KDE application in the image — Dolphin, Konsole and the
   window decoration — was rendering in Breeze *light* on a dark desktop. The scheme is now
   generated from the same tokens as `Theme.qml` into `/usr/share/color-schemes/`, in both
   variants, and `test_borrowed_theme.py` fails if kdeglobals ever names a scheme that is not
   installed. This also explains part of why borrowed KDE surfaces never looked like the shell.

### Run #29c — Kvantum: the widget style the global themes asked for but never shipped

Both Plasma packages set `widgetStyle=kvantum` in their `defaults` and shipped no Kvantum theme —
the KNS dependency list has none. So the engine and the skin were sourced separately:

* engine: `qt6-style-kvantum` 1.1.5-1, confirmed present in the resolute package index;
* theme: `Windows-modern` from github.com/Jeysef/KDE-Windows-Modern (GPL-3), which documents its own
  ancestry in `ATTRIBUTION.md` — Fluent-kde by vinceliuice and Win11OS-kde by yeyushengfan258.

This only touches **QWidget** applications: Dolphin, Konsole and every KDE dialog took their
buttons, tabs, scrollbars and menus from Breeze. Our shell is QtQuick and paints itself, so nothing
about the taskbar or Start changes — the goal is that opening Dolphin no longer looks like opening
KDE. Installed to `/usr/share/Kvantum`, selected in `/etc/xdg/Kvantum/kvantum.kvconfig` and in
`/etc/skel` (a live user has no home when the session starts), with `widgetStyle=kvantum-dark` in
kdeglobals — `kvantum` for the light build.

The same repository also carries its own Aurorae decorations and colour schemes. We keep
zayronXIO's for now because they are already measured and wired; comparing the two decoration sets
needs live captures, which is the open item of this cycle either way.

Tests: 124. Parity: 34/34.

### Run #29d — the ISO build died on a missing `xz`

All three variants failed at the theme step: `tar (child): xz: Cannot exec: No such file or
directory`. The icon fallback pack is vendored as a `.tar.xz` and the minimal rootfs has no
`xz-utils` — the same class of mistake as `kglobalacceld`: shipping something without checking that
the environment can actually use it. `xz-utils` is now installed alongside `git`, `ca-certificates`
and `gtk-update-icon-cache` in that chroot step, and a gate ties the two together: if the pack is a
`.tar.xz`, the theme step must install `xz-utils`.

### Run #30 — the three defects the live ISO showed

The first ISO that booted with the borrowed theme stack was also the first honest look at it. Three
things were wrong, and two of them had been invisible to the whole test suite.

**Alt+Tab did nothing.** Diagnosed in ADR-0012: KWin 6.6 ships one switcher layout and it imports
the Plasma QML stack we do not run, so it never loaded. We now ship our own layout,
`system/theme/tabbox/zaldros` — QtQuick plus `org.kde.kwin`, Windows 11 shape, tokens shared with
the colour scheme. It is loaded and checked in `tests/test_switcher.py` against stubs of KWin's
own types, so QML mistakes cost seconds instead of a 45-minute image build. Note the honest
limitation recorded in the ADR: Explorer and Settings live inside the shell window, so the switcher
sees one "Zaldros" entry rather than one card each.

**The Explorer window hung 60 px off the right edge.** It is placed at x=340 with a width of 1000,
which fits the 1600-wide design canvas and not a 1280x800 screen. Windows keep their designed
offset when it fits and are shrunk to the work area and centred when it does not. The reason no
test caught this is worse than the bug: `render()` resized the *window* but left the root item on
the design canvas, so every offscreen frame we have ever reviewed was drawn at 1600x1000 no matter
what size was asked for. Renders now resize the root item the way the live session does, and a test
renders at 1280x800 and asserts no window crosses an edge.

**The tray said "(UN".** `localectl` answers `(unset)` on an image where no keymap was configured,
and the badge was the first three characters of that. Unset values are now skipped — LANG answers
instead — and the badge is the Windows form: РУС, ENG, УКР. A layout we have no name for keeps its
own code rather than getting an invented one. The taskbar weather line no longer carries the
sentence "местоположение не задано" either; the state stays visible as a dimmed icon and a short
label, with the full explanation in the tooltip.

Tests: 134. Parity: 34/34.

### Explorer stops being a viewer

The file manager listed real files and could do nothing to them: the command bar was decoration.
Create, rename and delete now work, on the real filesystem, through `zaldros_shell/files.py`.

Three rules the implementation follows, all covered by `tests/test_files.py`:

* **Nothing is overwritten.** "Новая папка" becomes "Новая папка (2)" the way Windows counts, and a
  rename onto an existing name is refused with a sentence instead of silently replacing a file.
* **Delete means the bin, not oblivion.** `move_to_trash` writes the freedesktop `.trashinfo`
  record — encoded original path and deletion date — into `$XDG_DATA_HOME/Trash`, so anything
  deleted in Zaldros is restorable from Zaldros or from any other Linux file manager. Two files of
  the same name both survive in the bin.
* **A failure is a sentence, not a crash.** Every operation returns `files.Result`; the model puts
  the error into `errorText`, which Explorer already shows.

The UI follows Explorer: F2 or the command-bar button turns the row into a text field with the name
selected, Enter commits and Escape cancels; Delete removes to the bin; a new folder is created
selected and in rename mode; right-click opens the Windows 11 context menu with exactly the entries
that work. Double-clicking a file now hands it to `xdg-open` instead of doing nothing.

Tests: 147.

### The keyboard the image never had

Run #30's tray badge read "ENG" honestly — and that was the whole problem: the image had never
been told what keyboard it has, so `localectl` answered `(unset)` and LANG was the only source
left. A Russian-facing desktop ships two layouts.

`kxkbrc` now carries `LayoutList=us,ru` with `grp:alt_shift_toggle`, and `/etc/default/keyboard`
matches it for the console and X11 clients. The file matters: KWin reads layouts from **kxkbrc**,
group `[Layout]` (kwin v6.6.0 `src/main.cpp` opens it, `src/xkb.cpp` reads `LayoutList`,
`Options`, `ResetOldOptions`). Putting the same keys in kwinrc would have been ignored without a
word.

The badge now asks KWin instead of the image. On Wayland KWin owns the keyboard, so after the user
presses Alt+Shift only KWin knows which layout is active; the shell reads
`org.kde.keyboard /Layouts org.kde.KeyboardLayouts` (service name verified in
`src/keyboard_layout.cpp` — it is *not* org.kde.KWin) and falls back to localectl and then LANG
when KWin does not answer. Clicking the badge switches to the next layout, as it does in Windows.

Tests: 153.

### Run #33: the shortcut daemon that was never missing

Three runs blamed `kglobalacceld`. Run #33's log finally showed it plainly: the daemon exits `0`
the instant it starts, five times, because the D-Bus name it wants is already taken — by
`kwin_wayland` itself. kwin v6.6.0 embeds it: `src/main_wayland.cpp` has
`Q_IMPORT_PLUGIN(KGlobalAccelImpl)` and `src/globalshortcuts.cpp` constructs a `KGlobalAccelD`
in-process. The session no longer spawns a second one, and the probe confirms the component and
KWin's own `Walk Through Windows` action are registered on the bus.

So the shortcut side is healthy and the switcher still draws nothing, which leaves the drawing
side: `TabBoxHandlerPrivate::createSwitcherItem()` reports a broken package with a single
`qCWarning(KWIN_TABBOX)` and then returns quietly. That warning is written *while Alt+Tab is
pressed* — a hundred seconds after the boot self-test has printed its JSON and gone. Two changes
make the next boot answer instead of hint: the session exports
`QT_LOGGING_RULES=kwin_tabbox.debug=true`, and the boot ends with `zaldros-selftest --late`, run
after the host's Alt+Tab, which dumps the session log, every tabbox line in it, and the switcher
probe again.

Two suspects were removed on the way: the layout imports `QtQuick.Window`, so the image now
installs `qml6-module-qtquick-window` (a missing QML module is exactly that one silent warning),
and the root `currentIndex: grid.currentIndex` binding is gone — `grid` lives in the
Instantiator's delegate, a different component scope, and kwin sets that property itself.

Tests: 164.

### Run #34: the report that ate the build, and Alt+Tab moved out of KWin's tabbox

Run #33's diagnostics worked, and then killed the job. The `--late` report embeds the session
log; the session log already contained an echoed `ZALDROS-SELFTEST {...}` line; the host picked
the *last* marker on the serial log with `grep -o … | tail -1`, so it read that escaped copy and
`json.load` died on `{\"kernel\"…`. A boot that had passed every check was reported as a failed
build. Both halves are fixed: the guest scrubs any nested marker out of a report before printing
it (`marked()`), and the host no longer trusts position — `build/iso/extract_marked.py` tries every
candidate newest-first and takes the first one that parses. The late report now lands in the
artifact JSON as `late`, next to `ui_guest` and `ui_host`.

Reading run #33's late report through the new extractor gave the answer we paid 20 minutes for:
`tabbox_lines` is empty. Not a broken-package warning, not a QML error — with
`kwin_tabbox.debug=true` on, KWin's tabbox says *nothing at all*, which means it never activates.
Meanwhile the Meta key opens Start, so key injection works; but Start is handled by `Shell.qml`'s
own `Keys` handler, not by a global shortcut, so nothing in this session had ever proven that the
global shortcut path works end to end.

Alt+Tab therefore leaves KWin's tabbox, in line with ADR-0012: `system/theme/kwin-scripts/
zaldros-switcher` is a KWin script that registers `Alt+Tab` / `Alt+Shift+Tab`, walks
`workspace.stackingOrder` and sets `workspace.activeWindow` — and prints `ZALDROS-SWITCHER` for
every step, so the next boot shows whether the shortcut fired, whether it found windows, and which
one it activated. KWin's own `Walk Through Windows` binding is set to `none` (it registers first
and would otherwise keep the key), and the shortcut file is installed into `/etc/skel/.config` and
the live home as well as `/etc/xdg`, because kglobalaccel reads the user's copy first.

Three more instruments for the same boot: `kwin_environ()` reads `QT_LOGGING_RULES` out of the
live compositor's `/proc/<pid>/environ` (a rule that never reached KWin looks exactly like a
category with no output), `invoke_and_watch()` fires the action over D-Bus and reports what the
session log gained in the next 1.5 s — separating "the key never arrived" from "the action ran and
drew nothing" — and `/etc/xdg/menus/applications.menu` now exists, because 90 % of the session log
was one repeated `"applications.menu" not found` line pushing the real evidence out of every tail.

Tests: 178.

### Run #35: who actually holds Alt+Tab, measured in the running system

The KWin script from run #34 loaded — `js: ZALDROS-SWITCHER loaded, windows=0` is in the session
log — and the key still did nothing: `alt_tab` FAIL, `switcher_fraction` 0.0, `switched_fraction`
0.0, the frames byte-identical. This time the boot could say why, because kglobalaccel was asked
instead of guessed:

* `allShortcutInfos` on `/component/kwin` reported KWin's own **Walk Through Windows** still bound
  to `150994945` (Alt+Tab) and `285212673` (Meta+Tab), even though `/etc/xdg/kglobalshortcutsrc`
  and both user copies said `Walk Through Windows=none,Alt+Tab,…`. Blanking only the *current*
  field leaves the default in place and the default is what came back.
* The live `~/.config/kglobalshortcutsrc` had our action written into the **`[kwin]`** group as
  `Zaldros Walk Through Windows=,none,` — no keys. A KWin script registers into kglobalaccel's
  `kwin` component, so our separate `[zaldros-switcher]` group was never its home; it only created
  the phantom component `/component/zaldros_switcher` that `allComponents` now shows, with no
  action behind it. The conflict with KWin's live Alt+Tab is what emptied our binding.
* Firing KWin's own shortcut over D-Bus succeeded (`()`) and produced **zero** tabbox lines with
  `kwin_tabbox.debug=true` confirmed present in kwin's own `/proc/<pid>/environ`. KWin's tabbox is
  not slow or mis-themed here; it does nothing at all. ADR-0012 stands.
* Our probe call itself was wrong and said so: `invokeShortcut` does not exist on `/kglobalaccel`,
  only on `/component/<name>` (`org.kde.kglobalaccel.Component`). Fixed, and the report now dumps
  every `Walk Through` line of both config files instead of the last 1200 bytes.

So the fix is small and entirely in configuration: both fields `none` for KWin's two actions, our
two actions seeded inside `[kwin]` where they are autoloaded, and no group of our own. The script
also un-minimises the window it activates — the boot log shows Dolphin was minimised when Alt+Tab
fired, and KWin leaves an activated window minimised, which no person and no screen comparison
would ever call a switch.

Also from this run, from the public Windows 11 reference library: the desktop context menu was
drawing «Показать дополнительные параметры» straight through «Shift+F10». Windows 11 grows a menu
to its widest row; ours was pinned at 300 px whatever the language. `ContextMenu` now measures its
content (`TextMetrics`, the same row arithmetic the delegate uses) with 300 px as the floor, the
reference records `min_width` instead of `width`, parity gained a `min` comparator, and
`test_context_menu_fit.py` renders the menu and demands a real background gutter before the
shortcut column — a pixel gate, not a re-run of the layout maths.

### Run #35: a reference library anyone can check, and a menu that stopped talking over itself

Every geometry token in `win11-reference.json` was measured — but from screenshots that can never
be published, so nobody outside this machine could verify one of them. This run built the missing
half: `assets/refs/win11/library.json`, 36 authentic Windows 11 screenshots **published by
Microsoft** (Microsoft Learn, Microsoft Support, the Windows Insider and Windows Experience blogs,
the June 2021 press kit), covering all fifteen states we implement — desktop, taskbar, Start,
search, Settings, Explorer, context menus, Quick Settings, notifications, window decorations,
dark and light mode, dialogs, multiple windows and snap layouts.

The images stay out of the repository (Microsoft's copyright). `tools/visual/fetch_references.py`
downloads them into a gitignored cache and verifies the recorded sha256, so a reference that
changes upstream fails loudly instead of silently rewriting a measurement.

Two of them prove their own display scale, which is what makes a screenshot measurable at all:
`quick-access-update2.png` puts its caption glyphs 45.5 px apart against a 46 px caption button, so
it is a 100 % capture; the Quick Settings flyout is 536 px wide against a 360 px panel, so it is at
150 %. `tools/visual/measure_library.py` re-derives eight numbers from those two and all eight
agree with the committed reference — caption button width, context menu item height, and the Quick
Settings panel width, padding, tile width, tile height and gap that had only ever been measured
from private captures.

The comparison against the seven rendered states then found what geometry parity structurally
cannot see: the desktop context menu drew "Показать дополнительные параметры" straight through
"Shift+F10". `ContextMenu.qml` pinned every menu at 300 px whatever the language, while Windows 11
sizes a menu to its widest row. The menu now measures its rows with `TextMetrics` and treats 300 as
a floor (`context_menu.min_width`, checked with a `min` comparator instead of equality — the file
menu in the public 100 % capture is narrower than the desktop menu, so equality was never right).
The gate is pixel-based, not a second copy of the layout arithmetic:
`tests/test_context_menu_fit.py` renders the menu and fails when the gutter before a row's trailing
text drops below 8 px. Pinning the width back to 300 makes it fail, which is the only proof that a
regression test is worth anything.

Two measurements the library raises and this run deliberately did **not** act on: Explorer's
navigation pane measures 240 px at 100 % against our 190 token, and the details-view row pitch
measures 30 against our 32. The pane is user-resizable, so the capture may just show a wider one —
the maintainer's call, recorded in `docs/WIN11_REFERENCE_LIBRARY.md`.

Tests: 182. Parity: 34/34.

### Run #36: Alt+Tab was never pressed — the key name did not exist

Run #36's ISO built and booted 9/9, and `alt_tab` failed for the sixth consecutive time:
`switcher_fraction` 0.0, `switched_fraction` 0.0. Everything the boot could say about the system
said the system was fine — kglobalaccel reported our action `Zaldros Walk Through Windows` bound
to `150994945` (Alt+Tab) in the `kwin` component, KWin's own `Walk Through Windows` was finally
key-less, and firing the action over D-Bus produced `ZALDROS-SWITCHER cycle candidates=2` followed
by `activating Home — Dolphin`, restoring the minimised window exactly as intended. The switcher
worked. Only the key did nothing.

The key did nothing because it was never sent. `build/iso/ui-drive.py` held the modifier with
`key_state("alt_l", True)`, and **QKeyCode has no `alt_l`**: QEMU names the left Alt `alt`
(`qapi/ui.json`: `shift`, `shift_r`, `alt`, `alt_r`, `ctrl`, `ctrl_r`, … `meta_l`, `meta_r` — only
Meta and Shift/Ctrl carry an `_r` sibling, and none carries an `_l`). QEMU answered every one of
those events with `GenericError: Invalid parameter 'alt_l'`, and `QMP.cmd` read the reply and
threw it away. The guest received a bare Tab. Six runs, four of them full 20-minute image builds,
were spent auditing KWin's tabbox, kglobalacceld, the shortcut config, the layout list and the
QML switcher package — every one of those audits was answering a question about a key press that
never happened. Meta+Tab-style steps passed throughout because `meta_l` is a real name.

Three changes, in the order that matters:

* **A refused command is now an exception.** `QMP.cmd` raises `QMPError` on an `error` reply,
  records it, and every step reports `qmp_error` instead of measuring pixels after an input that
  was never delivered; the host report ends with `qmp_errors`, whose only acceptable value is
  empty. This is the actual defect — a driver that cannot fail is a driver that cannot measure.
* **`alt`, not `alt_l`.** `tests/test_ui_drive_keys.py` parses every key literal out of the driver
  and fails on any name outside the QKeyCode enum, so the next invented key name dies in CI in
  0.1 s instead of in a 20-minute build.
* **Four probe shortcuts**, in case the honest Alt+Tab still fails: the KWin script registers
  `Meta+F9`, `Alt+F9`, `Ctrl+Shift+F9` and `Meta+Tab`, each printing one `ZALDROS-PROBE` line, the
  host presses all four, and the late report lists which appeared (`probe_lines`) plus
  `shortcut_fired_by_key`, read before the D-Bus invocation so it can only reflect a real key.
  If none fire, the keyboard→kglobalaccel path is dead; if Meta+F9 fires and Alt+F9 does not, the
  Alt modifier is eaten; if Alt+F9 fires and Meta+Tab does not, Tab is. One boot, three answers.
  The probes are seeded in `kglobalshortcutsrc` because an unseeded action is autoloaded as
  `,none,` (run #35) and would look exactly like a probe that failed to fire.

Tests: 188. Parity: 34/34.

### Win+V: the clipboard, not a picture of one

The maintainer's capture of the Windows 11 clipboard flyout set the target; the flyout is now real.
`zaldros_shell/clipboard.py` holds the history with Windows' own rules, checked by
`tests/test_clipboard.py`: 25 entries, a re-copy moves an entry to the top instead of duplicating
it, a pinned entry is never pushed out, and «Очистить все» removes everything *except* the pinned
cards. `model.ClipboardModel` listens to `QClipboard::dataChanged`, so every card is something
that was really copied in this session — text as text, a bitmap written into
`$XDG_CACHE_HOME/zaldros/clipboard` with only the path kept in the list. Clicking a card puts the
entry back on the clipboard (Windows then pastes it into the focused field; pasting into a window
we do not own is not ours to fake).

One rule is ours rather than Windows': **only pinned entries are written to disk.** An unpinned
history that outlives the session is a privacy leak; the pins live in
`$XDG_CONFIG_HOME/zaldros/clipboard-pinned.json` and are the only part that survives a reboot.

Geometry from the same capture at 125 %: panel 448 px = **360 logical** (the width every Windows 11
flyout has), cards 96 px = 76 with an 8 px gutter. Recorded in `win11-reference.json → clipboard`
with its provenance, and `tools/visual/parity.py` now renders a `clipboard` state and checks the
panel: **36/36**.

Not drawn, deliberately: the emoji / GIF / kaomoji / symbol tabs that share that Windows window.
A tab that opens nothing is exactly the decoration this project refuses to ship; they come with
their own data or not at all. And Win+V currently works while the desktop has focus — a
session-wide binding needs the global-shortcut path Alt+Tab is still proving out, and it gets
wired the moment that path has a passing boot verdict rather than on the assumption it will.

Tests: 201. Parity: 36/36.

### Run #37 — Alt+Tab worked; the test was watching the wrong second

The probes added in run #36 answered the question in one boot (iso 33108866212, all three variants,
all three profiles). From `boot-full-modern`:

- `qmp_errors: []` — every key really left the host this time.
- `probe_lines: ["-PROBE meta_f9", "-PROBE alt_f9", "-PROBE ctrl_shift_f9", "-PROBE meta_tab"]` —
  **all four** combinations reached a global shortcut, Alt among them.
- `shortcut_fired_by_key: true`, and the switcher's own log:
  `ZALDROS-SWITCHER cycle reverse=false candidates=1` → `nothing to switch to`.

So the key was pressed, kglobalaccel routed it, our KWin script ran, found **one** window and
correctly did nothing. The same script switched fine seconds later when the late report invoked it
over D-Bus with two windows open (`candidates=2`, `activating Home — Dolphin (was __main__.py)`).
Alt+Tab has worked since run #36; the harness has been photographing an empty desktop.

Why: the driver started the Alt+Tab step as soon as it saw `ZALDROS-GEOMETRY`, which the **shell**
prints seconds after login — 45 s before stage 2 launches Dolphin. Six FAILs came from measuring a
switch that had nothing to switch to.

The fix is in the test, not the product:
- `uitest.py` prints `ZALDROS-WINDOWS-READY {...}` the moment KWin confirms the second window, and
  before it starts moving, minimising and restoring it.
- `ui-drive.py` waits for that line (`second_window` / `wait_for_second_window`, ≤180 s), then for
  stage 2's own end marker (`wait_for_marker`, ≤90 s) so nobody else is changing the screen, and
  only then presses Alt+Tab. Without the line the step is `BLOCKED` with the reason, never `FAIL`.
  Escaped copies of the marker inside embedded logs are ignored, as `marked()` sanitising in
  `selftest.py` and a test both ensure.
- The late report gained `switcher_cycles` and `alt_tab_switched` — the switcher's verdict in its
  own words, read before the D-Bus invoke fires one itself.
- Stage 3's pause grew 30 s → 45 s to cover the longer, evidence-driven wait.

Six new tests in `tests/test_ui_drive_keys.py` hold the sequencing in place. Tests: 207.
Parity: 36/36.

### Win+G: a capture panel that only offers what the machine can do

The maintainer's capture of the Windows «Записать» widget set the target: a 383 × 274 px panel at
125 % with four 70 px tiles on a 90 px pitch and a «Просмотреть мои записи» row under a divider.
Divided by 1.25 that is 306 × 219, tiles 56 on a 72 pitch, padding 17 — recorded in
`win11-reference.json → game_bar` with its provenance and checked by parity: **38/38**.

What is behind the tiles matters more than their size. `zaldros_shell/capture.py` resolves every
capability to an executable that actually exists in `PATH` (spectacle → portal → grim for stills,
ffmpeg → wf-recorder for video) and builds the exact command; `zaldros_shell/portal.py` performs
the four-call `org.freedesktop.portal.ScreenCast` handshake, because on Wayland no application may
read the framebuffer without the compositor's consent — the PipeWire node it returns is what
ffmpeg's `pipewiregrab` reads. `model.GameBarModel` reports a screenshot as taken **only when the
file is on disk**, and a recording command is never built without a node, which would have
produced a black rectangle called a video.

Where a capability is missing, the tile is disabled and the panel prints the reason
(«Запись недоступна: нужен ffmpeg, wf-recorder и портал захвата экрана…»). The «last 30 seconds»
tile is permanently one of those: it needs a ring buffer the compositor does not offer us, and
saying so is more honest than a button that does nothing. The ISO now installs `kde-spectacle`,
`xdg-desktop-portal(-kde)` and (in `full`) `ffmpeg`, plus `python3-pyside6.qtdbus` — caught by
`test_iso_packages.py`, which noticed the new import before CI did.

Captures go where Linux keeps them, read from `user-dirs.dirs`: `<Изображения>/Zaldros/Снимки
экрана` and `<Видео>/Zaldros/Записи`.

Boot evidence, not assumption: `uitest.py` gained a `screenshot` step that runs the same grabber in
the booted ISO and passes only if a non-empty file appears; `report.py` shows it in the matrix.

Five more Fluent icons (MIT) vendored: camera, record, microphone, microphone-off, history. The
licence tables were also corrected — they still claimed 26 vendored glyphs when the directory has
90.

Tests: 230. Parity: 38/38.

### The game bar was a widget without its bar — and the decoration is ours now

The maintainer's verdict on the first Win+G cut was blunt and correct: «это и близко не как на
скрине». Two things were wrong. The floating **bar** — the pill at the top of the screen that owns
the widgets — was not drawn at all, and the capture widget's tiles had outlines Windows does not
draw.

`GameBarToolbar.qml` is that bar, measured from the same capture: 654 × 67 px at 125 % = **523 × 54**
logical, buttons on a 50 px = 40 pitch, the active widget button a filled light tile with a dark
glyph. Three groups, as Windows lays them out: what is running on the left, the widget buttons on
their own lighter field in the middle, clock/battery/settings on the right. Xbox friends and Edge
are not drawn — they are not ours to fake — and the field is sized to the buttons it holds, the way
Windows sizes it to five. Parity now checks the bar's width, height and that it is centred: **41/41**.

Its readings are the same real ones the taskbar uses (`ShellState.timeText`, `SystemState.battery*`),
and the camera button lights up exactly while the capture widget is open.

`GameBarPerformance.qml` is the second widget, so the performance button opens something rather than
nothing: CPU load from the difference between two `/proc/stat` samples (`backend.cpu_times` +
`cpu_percent`, `-1` until two exist), memory from `/proc/meminfo`. GPU and FPS are named as *not
measured* instead of drawn.

**The window decoration is ours.** `tools/theme/make_aurorae.py` generates
`assets/themes/aurorae/Zaldros{,-Dark}` — nine slices plus their inactive twins, five states for
each of seven buttons, all from `win11-reference.json → window` (title bar 32, caption buttons
46 × 32, corners 8). The borrowed GPL-3 `Windows-Eleven` decorations are deleted from the tree and
from the notices; after this the cursor pack is again the only borrowed thing, as ADR-0010 says.
`tests/test_aurorae_theme.py` regenerates both variants and fails if a committed file differs, so a
hand-edited SVG cannot drift away from the measurements. Whether KWin renders it as intended is a
question for the next boot's screenshot, not for this paragraph.

Tests: 251. Parity: 41/41.

## 2026-08-27 — the decoration, as KWin actually drew it

The first boot with our own Aurorae theme (iso run `33113315031`, commit `74ed6d7`) answered the
question the previous entry left open: KWin rendered the title bar, and the caption buttons came out
as two white blocks and an X the size of a fist. The cause is in Aurorae, not in the SVG source —
it paints an element by id and scales it to that element's **bounding box**. Our states held only
the glyph, so a 10 px cross was stretched over the whole 46 × 32 button. The nine decoration slices
had the milder version of the same bug: their 1 px frame was a *stroke*, which inflates the box by
half a pixel, so every slice was drawn 0.5 px off its slot.

Both are fixed by geometry, not by fudge factors. Each button state now carries an invisible
full-size rect, and the frame lines are filled 1 px rects and filled corner paths instead of
strokes. Measured with `QSvgRenderer.boundsOnElement`: all five states of all seven buttons are
exactly 46 × 32, and each of the nine slices reports exactly its own slot — two new tests assert
precisely that, so this cannot come back silently.

`tools/theme/preview_aurorae.py` composes the theme the way Aurorae does (fixed corners, stretched
middles, buttons in their slots) and writes a PNG. That is the point of it: this class of mistake is
invisible in SVG text and obvious in a picture, and a picture costs a second instead of an hour-long
ISO build.

Boot evidence from the same run, all PASS: alt_tab (switcher visible, `switched: true`, 47.5 % of
the frame changed, second window `Home — Dolphin` after 44 s), start_open/start_close (45.4 %),
taskbar_response, and the in-guest `screenshot` step via `spectacle` (312 186 bytes). `qmp_errors:
[]`.

Tests: 253. Parity: 41/41.

## Цикл 4b — hairline-точные глифы кнопок заголовка

Максим прислал эталон (Windows 11, тёмная тема, 125 % масштаб): три глифа шириной 13 px с шагом
57 px, чисто белые `#ffffff`, толщина линии 1 px без размытия. Пересчёт на 100 %: кнопка 46 px,
глиф 10 px — наша геометрия совпала. Не совпадала резкость: в `tools/theme/make_aurorae.py`
глифы строились от центра кнопки (23, 16), поэтому штрих шириной 1 px с центром на целой
координате рисовался двумя полупрозрачными рядами — серая каша вместо белой линии.

Исправлено: все штрихи привязаны к полупиксельной сетке (`x.5`), `stroke-linecap="butt"`,
прямоугольники — `x + 0.5 / size - 1`, «восстановить» перерисован по эталону (передний квадрат
8 px, задний выступает на 2 px вверх-вправо со скруглением). Проверено измерением отрисованных
пикселей, а не глазами: у «свернуть» ровно один полностью белый ряд, у «развернуть» — два.

Новый тест `test_glyph_hairlines_land_on_whole_pixels` в `tests/test_aurorae_theme.py`.
Гейты: 198 passed + 1 skipped (shell), 44 passed (tools), паритет 41/41.

## Цикл 5 — Zaldros Sheets: своё окно, движок LibreOffice

Задача владельца: таблица, которая выглядит как современный Excel, но считает не наша.

**Исследование.** Четыре пути проверены по первоисточникам. **LibreOfficeKit** (`paintTile`,
`postKeyEvent`, `postUnoCommand`, `LOK_CALLBACK_*`) — единственный способ получить пиксели самого
движка под нашей рамкой; на нём работают Collabora Online и LibreOffice для Android. Но заголовки
требуют `LOK_USE_UNSTABLE_API`, привязки к Qt/QML не существует ни одной, а GTK-виджет
`lokdocview` внутри Qt-процесса падает. **UNO** — стабильный API к модели документа, но рисовать
не умеет вовсе. **Форк ядра** — в `sc/` UI и модель перемешаны, шва «свой фронтенд» там нет,
сборка часы и десятки гигабайт. **Тема VCL** — ленту не сделает.

**Решение (ADR-0013).** UI наш, движок LibreOffice, всегда. Канал первый — UNO: открытие, ячейки,
формулы, сохранение. Канал второй, позже — LOK для того, что умеет рисовать только движок
(диаграммы, условное форматирование, предпросмотр печати). `soffice` — дочерний процесс на
локальном сокете: лицензия остаётся обязательством по распространению неизменённого пакета, а
падение движка не роняет окно.

**Сделано и измерено.**
- `apps/sheets/zaldros_sheets/engine.py` — мост к движку. 6 тестов на живом LibreOffice:
  `=SUM(A1:A2)*1.5` → 63, `=1/0` → ошибка движка дословно, XLSX туда-обратно с формулой и текстом.
- Своё окно на QML: зелёная шапка с AutoSave, лента с вкладками и скруглённой карточкой, строка
  формул с полем имени и `fx`, сетка с заголовками строк и столбцов, вкладки листов, строка
  состояния. Каждый размер — из `system/theme/excel-reference.json`.
- Геометрия измерена с собственных снимков Microsoft (Excel 365 после редизайна 2023, светлая и
  тёмная темы): якорь — строка сетки, 38 устройственных px против 20 px при 100 %, отсюда масштаб
  1,9. Шапка 52, полоса вкладок 33, карточка ленты 105, строка формул 23, заголовок столбцов 20,
  строка 20, заголовок строк 29. Цвета: `#107c41`, `#e9eef2`, `#f0f0f0`, `#e0e0e0`; тёмная тема —
  `#1c2227`, `#292929`, акцент `#60bd82` (осветлённый тот же тон, не другой цвет).
- `assets/refs/excel/library.json` — 9 подлинных снимков Microsoft с URL и sha256, файлы не
  коммитятся; `tools/visual/fetch_references.py --library excel` их скачивает и сверяет.
- 6 тестов на окно измеряют отрисованный PNG против токенов.
- Пробелы записаны честно: предпросмотр печати, параметры Excel, строка состояния крупным планом,
  контекстное меню ячейки, полные вкладки Data/Review/Page Layout/Formulas — подлинных снимков не
  нашлось, поверхности не строятся, пока их нет.

Гейты: apps/sheets 12 passed; shell 198 passed + 1 skipped; tools 44 passed; паритет 41/41.

## 2026-08-27 — один backend вместо десятка Linux API (ADR-0014)

**Задача.** Довести системный backend: systemd, NetworkManager, PipeWire, BlueZ, UPower, udisks2,
polkit, дисплей, питание, железо, уведомления, службы — и увести UI с прямых обращений к ним.
Дизайн не трогать: это жёсткий гейт.

**Исследование.** Прочитаны первоисточники (freedesktop D-Bus spec, NetworkManager, UPower, logind,
systemd1, polkit, notification spec, BlueZ Adapter/Device, udisks2 Drive/Block/Filesystem) и
манифест Ubuntu 26.04: systemd 259.5, bluez 5.85, udisks2 2.10.91, upower 1.91.1, pipewire 1.6.2
[ubuntu-26.04-desktop-amd64.manifest, 2026-08-27]. Три вывода изменили архитектуру:
- PipeWire **не на D-Bus** — громкость идёт через libwireplumber/`wpctl`, интерфейса громкости нет;
- яркость: `org.kde.ScreenBrightness` (Plasma 6.5+) → старый `Solid.PowerManagement` (максимум
  нормализован в 10000, не сырой sysfs) → sysfs только на чтение;
- список выходов монитора — это протокол Wayland `kde-output-management-v2`, не D-Bus, поэтому
  `kscreen-doctor -j`.

**Измерение, которое решило вопрос зависимостей.** QtDBus в PySide6 не умеет разобрать `a{sv}`:
`QDBusArgument.asVariant()` возвращает нулевой конвертер, любой словарь свойств приходит как `None`.
А словарь свойств — это ровно то, чем отвечают UPower, NM, BlueZ, udisks2 и systemd. Ставить
python3-dbus в CI нельзя (у приложения нет права `workflows`), поэтому написан свой клиент D-Bus
без зависимостей: `wire.py` (маршалинг), `connection.py` (сокет, SASL EXTERNAL, match rules),
`service.py` (серверная сторона), `bus.py` (нераскидывающийся фасад с `Result`).

**Сделано.** `backend/zaldros_backend/` — фасеты power, network, bluetooth, audio, storage, display,
services, session, notifications, auth, hardware; единая точка `ZaldrosBackend` и единственный
Qt-зависимый файл `qtbridge.py` (QSocketNotifier + склейка событий на 120 мс). Всё возвращает
`Reading(available, value, detail, source)` — «нет данных» отличается от «нет службы» и от «не
поддерживается». Оболочка теперь ходит только сюда: `system.py` стал тонким швом, `/proc` из
`backend.py` и `hostinfo.py` убран.

**Баг, который нашёл только честный стенд.** Диспетчер сигналов не проверял отправителя, а
`sender` в сигнале — уникальное имя (`:1.7`), не well-known. Из-за этого `InterfacesAdded` от
udisks2 будил обработчик BlueZ. Видно стало лишь тогда, когда каждый мок получил своё соединение.
Исправлено разрешением well-known → unique при подписке.

**Убрано лишнее.** Таймер на 1 с, круглосуточно читавший `/proc/stat` и `/proc/meminfo` и
дёргавший перерисовку, заменён: состояние железа приходит событиями, часы — одноразовый таймер до
следующей минуты и сигнал только при смене текста, счётчики CPU/RAM считаются только пока открыто
меню «Пуск» или панель производительности игровой панели.

**Измерено** (`tools/zaldros-bench/backend_overhead.py`, оба режима в одном запуске, 300 с простоя):
CPU 0,11 с → меньше порога учёта ядра (10 мс); 22,0 мс/мин → < 2; чтений `/proc` 1200 → 0;
сигналов модели 300 → 5. `voluntary_ctxt_switches` под этим ядром не растёт — счётчик помечен
негодным, а не выдан за ноль. Подробности: `docs/state/measurements/2026-08-27-backend-overhead.md`.

**Дизайн-гейт доказан пикселями.** Кадры до и после отрисованы и сравнены: разница только в
прямоугольнике 6×8 px на часах панели задач (22:38 против 22:37), у колонки виджетов bbox разницы
пустой. Паритет 41/41.

Гейты: shell 303 passed + 1 skipped + 1 fail (заранее известный сбой отрисовки трея в песочнице,
воспроизводится и на чистом HEAD); tools 44 passed; паритет 41/41. Тестов в оболочке 207 → 304.

**Чего нет и о чём не надо думать, что оно есть.** `org.zaldros.Backend1` на шину не выставлен —
приложения импортируют пакет. Сервер уведомлений написан и покрыт тестами, но имя
`org.freedesktop.Notifications` в рантайме не занимает. Ничего из этого не проверено на живом
железе: первым доказательством будет отчёт о загрузке ISO.

## 2026-08-28 — «Параметры» перестали быть картинкой (ADR-0015)

**Задача.** Оживить Settings целиком: дисплей, разрешение, частота, масштаб, несколько мониторов,
звук, микрофон, Wi-Fi, Ethernet, Bluetooth, питание, батарея, клавиатура, мышь, тачпад, язык,
часовой пояс, уведомления, приватность, брандмауэр, пользователи, приложения, приложения по
умолчанию, память, обновления, восстановление. Проверка — обратный цикл: UI → backend →
состояние системы → UI показывает состояние.

**Что сделано.** Между строкой «Параметров» и backend встал реестр контролов
(`settingscontrols.py`, 63 контрола на этой машине): у каждого `read()` и `write()`, четыре вида
строк (`switch`, `choice`, `action`, `info`) и обязательные `available` / `writable` / `reason`.
После записи значение **перечитывается из системы** — UI показывает ответ машины, а не намерение
клика. Ползунки сделаны дискретным выбором на вложенной странице тех же карточек: настоящая запись
сегодня вместо нового виджета когда-нибудь, и визуальный гейт не тронут.

**Новые фасеты backend** (каждый — с первоисточником в `catalog.py`): `localetime` (timedate1 +
locale1), `inputdevices` (KWin `org.kde.KWin.InputDevice` — проверено по исходникам kwin
`src/backends/libinput/{connection.cpp,device.h}`), `accounts` (accountsservice), `permissions`
(портал разрешений, таблицы `devices` и `location`), `updates` (PackageKit — транзакция + сигналы,
а не один вызов), `firewall` (ufw через `/etc/ufw/ufw.conf` + `pkexec`, firewalld через D-Bus),
`defaultapps` (`mimeapps.list`, атомарная запись), плюс `power.firmware_setup` (logind
`SetRebootToFirmwareSetup`) — это и есть «восстановление».

**Честность, которую пришлось защищать кодом.** «Брандмауэр не установлен» и «брандмауэр выключен»
— разные факты; PackageKit, который не ответил, — это не «обновлений нет»; переключатель
приватности не пишется, если ни одно приложение ещё не спрашивало (wildcard-строки в базе портала
нет); опция, которой у железа нет (`supportsDisableEvents` у мыши), не пишется, а отказывается.
Тест `test_on_a_machine_with_no_services_every_control_is_unavailable_and_none_invents_a_value`
проходит по всем контролам на машине без единой службы и требует: нет значения — есть причина.

**Переключатели оболочки теперь тоже что-то делают.** `notifications.banners/dnd/sound` попадают в
политику сервера уведомлений (`policy_from`): баннеры выключены — уведомление остаётся в центре,
«не беспокоить» ещё и молчит, критическое (urgency 2) проходит всегда. `privacy.recent_files`
выключает сбор недавних файлов, `clipboard.history` — запись в журнал Win+V (копирование работает,
журнал пуст).

**Гейты.** shell 346 passed + 1 skipped + 1 fail (известный сбой отрисовки трея в песочнице);
tools 44 passed; паритет 41/41. Кадры до/после отличаются только прямоугольником часов на панели —
дизайн не менялся.

**Чего нет.** Ничего из этого ещё не проверено на живом железе: в песочнице нет ни kscreen-doctor,
ни портала, ни accountsservice, поэтому все страницы показывают причины отсутствия. Первым
доказательством будет отчёт о загрузке ISO. Не сделано: ночной свет, профили питания PowerDevil,
создание и удаление пользователей (нужен подтверждающий диалог, а половинчатая кнопка «удалить» —
худшая кнопка в настройках), VPN и прокси.

## 2026-08-28 — «Диспетчер задач»: настоящие процессы, и ноль чтений, пока он закрыт (ADR-0016)

**Задача.** Полноценный Task Manager: приложения, процессы, службы, ЦП, память, GPU, диск, сеть,
время работы, автозагрузка; завершение процесса, инспекция, сортировка, поиск, графики. Условие
владельца — никаких выдуманных метрик. Условие ADR-0014 — никакого фонового опроса.

**Исследование.** Структура окна взята из документации и публикаций Microsoft о переработанном
диспетчере (Windows 11 22H2+): вертикальный рельс страниц вместо верхних вкладок, командная панель
с поиском и «Снять задачу», разделы «Приложения / Фоновые процессы / Процессы Windows»
[Windows Insider Blog, Microsoft Learn, 2026-08-28]. Подлинного снимка в библиотеке эталонов нет —
геометрия взята из уже измеренных токенов Windows 11 и помечена в `win11-reference.json` как
производная, а не как измерение.

**Сделано.** `backend/zaldros_backend/processes.py` — фасет над файлами ядра (`/proc/<pid>/{stat,
status,cmdline,io,fd}`, `/proc/stat`, `/proc/meminfo`, `/proc/diskstats`, `/proc/net/dev`,
`/sys/class/drm`), без `ps`, `top` и psutil. `zaldros_shell/taskmanager.py` — сортировка, поиск и
формат колонок без Qt. `ProcessModel` и `StartupModel` в `model.py`, окно `qml/apps/TaskManager.qml`
с тремя страницами, Ctrl+Shift+Esc и кнопкой на панели задач только пока окно открыто.

**Три правила, которые проверяются тестами, а не обещаются.**
- Первая выборка не знает загрузки: `cpu is None`, колонка показывает «—». Ноль вместо неизвестного
  — это выдуманная метрика.
- Закрытое окно не читает ничего: тест со счётчиком выборок показывает 0 до открытия и остановку
  таймера после закрытия.
- Раздел «Приложения» пуст без композитора и объясняет почему, вместо эвристики по именам.

**Мелочи, которые ловятся только на настоящем ядре.** Имя процесса берётся по последней `)`, а не
по пробелам (`Web Content (tab)` ломает наивный парсер). Разделы не считаются внутри своих дисков
(`sda1` внутри `sda`, `nvme0n1p1` внутри `nvme0n1`). `lo` исключён из сетевых счётчиков.
Недоступный `/proc/<pid>/io` — это «неизвестно», а не ноль. Alt+Tab теперь обходит только открытые
окна: полный список идентификаторов *запускал* бы диспетчер задач.

**Завершение процесса** — SIGTERM, по явному требованию SIGKILL, pid ≤ 1 отклоняется; ответ ядра
(EPERM и т. п.) выводится дословно. Проверено настоящим убийством настоящего `sleep`.

**Дизайн-гейт.** Семь кадров (рабочий стол, «Пуск», быстрые параметры, «Параметры», «Проводник»,
центр уведомлений, светлая тема) отрисованы с HEAD `89975d5` и с этой веткой и сравнены попиксельно:
**все семь идентичны, разницы нет вообще**. Паритет 41/41.

Гейты: shell 372 passed + 1 skipped (было 347); tools 44 passed; паритет 41/41.

**Чего нет.** Живого железа не видело ничего: в песочнице нет GPU с `gpu_busy_percent` и нет
разделов с настоящим вводом-выводом. Графики только для ЦП и памяти, история живёт в памяти окна.
Страница «Службы» пока не выведена в окно (фасет `services` из ADR-0014 готов). Раздел
«Пользователи» и «Журнал приложений» не делались.

## 2026-08-28 — «Диспетчер устройств»: sysfs как единственный источник (ADR-0017)

**Сделано.** `backend/zaldros_backend/devices.py` — дерево категорий в порядке Windows, устройства
из `/sys/bus/{pci,usb}`, `/sys/class/{net,block,drm,video4linux}`, DMI, `/proc/bus/input/devices`,
`/proc/asound/cards`, очереди CUPS. `DeviceModel` в `model.py` и окно `qml/apps/DeviceManager.qml`
(дерево слева, свойства справа, «Обновить конфигурацию оборудования»).

**Честность кодом.** Неразрешённое имя остаётся идентификатором `dead:beef`; устройство без
привязанного драйвера помечено, а не скрыто; пустая категория несёт причину («ядро не показывает
/sys/bus/pci/devices в этой среде»). `lo`, разделы, `loop`, корневые USB-хабы и интерфейсы,
отключённые выходы DRM отфильтрованы — каждое исключение проверено тестом.

**Гейты.** shell 386 passed + 1 skipped; tools 44; паритет 41/41; семь кадров до/после отличаются
только прямоугольником 8×8 px на часах (08:44 → 08:54).

**Чего нет.** Модули DIMM, серийники и SPD требуют root. Отдельной ветки Bluetooth из BlueZ пока
нет. Обновление/откат драйверов не делались. Живого железа ничего не видело: в песочнице нет ни
PCI, ни USB, ни DRM — поэтому все ветки показывают причины.

## 2026-08-28 — Сеть, звук, Bluetooth, питание: появились пути записи (ADR-0018)

**Сделано.** Wi-Fi с паролем (`AddAndActivateConnection`, SSID байтовым массивом), отключение и
деактивация подключений, список сохранённых профилей и VPN с включением/выключением, DNS из
`IP4Config` активного подключения, прокси из переменных окружения (с честным `source`), сопряжение
и удаление устройств Bluetooth, громкость по приложениям и выбор устройства записи через `wpctl`,
режимы питания через power-profiles-daemon.

**Строки «Параметров» создаются по факту машины:** один переключатель на профиль VPN, один
регулятор на звуковой поток. Профилей нет — строк нет, а не «нарисованный список из трёх».

**Что ловят тесты (моки служб на настоящем dbus-daemon, проверяется то, что ушло на шину).**
SSID уходит `ay`, а не строкой; у открытой сети секции `802-11-wireless-security` нет вообще
(пустая заставила бы NM просить несуществующий ключ); `Pair` сопровождается `Trusted`;
`RemoveDevice` уходит адаптеру, а не устройству; громкость 900 % зажимается в 1.50.

**Гейты.** shell 407 passed + 1 skipped; tools 44; паритет 41/41; семь кадров до/после отличаются
только прямоугольником часов на панели.

**Чего нет.** Агента сопряжения BlueZ (устройство с PIN-кодом вернёт ошибку — она показывается),
ручной настройки прокси, создания и редактирования профилей VPN. Живого железа ничего не видело.

## 2026-08-28 — Терминал: настоящий pty и свой разбор VT (ADR-0019)

**Сделано.** `backend/zaldros_backend/terminal.py`: `PtySession` (fork на pty, `TIOCSWINSZ`,
неблокирующее чтение, код выхода), `Screen` (разбор xterm: курсор, стирание, вставка/удаление
строк, область прокрутки, SGR включая 256 цветов и truecolor, альтернативный экран, OSC-заголовок),
`profiles()` — только те оболочки, которые на машине есть. `TerminalModel` читает через
`QSocketNotifier`, без таймера. Окно `qml/apps/Terminal.qml`: вкладки, «+» со списком профилей,
панели рядом, Ctrl+Shift+T/W/D/C, стрелки и Ctrl+буква уходят в оболочку.

**Три бага, которые нашли тесты, а не глаз.** UTF-8, разорванный между чтениями из pty («привет»
превращался в ромбики) — хвост неполной последовательности теперь переносится. LF опускает строку,
но не возвращает каретку (иначе ломается `less`). Альтернативный экран (vim, less) не попадает в
буфер прокрутки оболочки.

**Проверено на настоящем bash:** `echo` доходит, `stty size` показывает те размеры, которые мы
задали pty (и меняется при resize), цвет от `printf` разбирается в атрибут, выход с кодом 3
виден как `exit_status == 3`.

**Гейт поймал ещё одно.** Тест покрытия глифов упал: у оболочки не было иконки терминала. Она
нарисована своя (`assets/icons/fluent/terminal.svg`, GPL-3, по сетке Fluent 20×20), а не взята из
чужого набора.

**Гейты.** shell 432 passed + 1 skipped; tools 44; паритет 41/41. Кадры до/после: единственная
заметная разница — часы на панели; в акриловой панели «Пуск» отличие не превышает 1/255 (шум
растеризации, визуально кадры совпадают).

**Чего нет.** Выделения мышью и полосы прокрутки (буфер хранится, UI рисует видимый экран),
bracketed paste, файла настроек в духе `settings.json`, подбора моноширинного шрифта. zsh, fish и
pwsh появляются в списке только если установлены — в песочнице их нет, проверены bash и sh.

## 2026-08-28 — Zaldros Writer: окно Word на движке LibreOffice (ADR-0020)

**Сделано.** `apps/writer`: мост к движку (живой документ по UNO + `convert()` через
`soffice --convert-to`), модель Qt, окно с лентой Word, страницей A4 и строкой состояния.
Абзацы, стили, полужирный/курсив/подчёркивание, таблицы, изображения, DOCX/ODT/RTF/TXT, экспорт
в PDF, число страниц из пагинации движка.

**Главное про честность.** В песочнице стоит `libreoffice-calc-nogui`, а Writer'а нет. Поэтому:
`writer_available()` проверяет наличие `libswlo.so`; ошибка называет недостающий пакет вместо
движковой загадки «type detection failed»; модель без документа отклоняет правки и показывает
причину на экране; тесты движка **пропускаются громко** — зелёный прогон здесь ничего не сказал бы
о работе с текстом.

**Геометрия выведена, а не измерена.** `system/theme/word-reference.json` получен из измеренного
снимка Excel (одна лента Office после 2023) и сам это объявляет.

Гейты: apps/writer 9 passed + 6 skipped (движок отсутствует); shell 432 + 1 skipped; tools 44;
паритет 41/41.

**Чего нет.** Ввода с клавиатуры в страницу, рецензирования, оглавления, сносок, колонтитулов,
печати из UI, и любой проверки на живом Writer.

## 2026-08-28 — Гейты, которые лгали в обе стороны (ADR-0021)

**Повод.** Попросили собрать ISO. В песочнице это невозможно: `unshare -rm --map-root-user` даёт
uid 0, но замаплен ровно один uid, поэтому configure-фаза dpkg падает
(`dpkg-statoverride: error setting ownership of '/var/lib/chrony': Invalid argument`) и за ней
рассыпаются `dbus`, `libpam-systemd`, `network-manager`, `plasma-desktop`. Дошло до `apt-install`
(exit 100) после 907 распакованных пакетов; `mksquashfs` и `grub-mkrescue` не запускались.
`/dev/kvm` тоже нет. `fakeroot` не применялся сознательно: он записал бы фиктивных владельцев в
squashfs. Скрипты сборки при этом не менялись — обходные пути жили во внешней обёртке.

**Зато нашлись настоящие дефекты гейтов.** Прогон `iso` 33157358995 на `b85017e` собрал три ISO
(`iso-full` 3 038 491 745 Б) и загрузил 9 образов из 9 на KVM — а матрица результатов в summary
была пуста: `build/iso/report.py` падал с
`AttributeError: 'dict' object has no attribute 'splitlines'`, потому что `boot_time` давно стал
словарём из `selftest.boot_seconds()`. Шаг был зелёным, потому что `| tee` возвращает свой код —
он же прятал и `return 1`, которым отчёт сообщает «что-то не загрузилось».

**И обратная ложь.** `test_the_shell_survives_a_machine_with_no_services_at_all` держал CI красным
шесть коммитов подряд (с `5f44ab9`, прогон 33124081665). Код был прав, тест — нет: обрезав шины,
он продолжал читать `/sys` хоста, у раннера поднят кабель, и `network` честно отвечал
`available=True, value=None`. Это и есть контракт Ethernet (уровня сигнала у провода нет,
«100 %» были бы выдумкой). Тест теперь подменяет `sysfs_root` пустым каталогом для network,
bluetooth и power и требует, чтобы всё было недоступно и объяснено; отдельный тест закрепляет, что
`available` значит «факт настоящий», а не «есть число».

**Что изменено.** `report.py` понимает обе формы `boot_time` (kernel+userspace, иначе uptime,
иначе прочерк); в шаге «Result matrix» появился `set -o pipefail` — в `docs/ci/iso.yml`
(живой `.github/workflows/iso.yml` пушить нельзя: у GitHub App нет права `workflows`, две строки
применяет владелец); `tests/test_boot_report.py` проверяет матрицу на форме, которую
реально пишет гость, код возврата на упавшей загрузке и рецензируемую копию workflow на `pipefail`; `BUILD.md`
переписан — там больше не написано «the build has never been executed», зато написано, что было в
прогоне, и что живого железа не видел никто; `TODO.md` приведён в соответствие.

**Гейты.** shell 441 passed + 1 skipped (было 432, все новые — тесты), tools 44, паритет 41/41.
Кадры до/после не снимались: под `zaldros_shell/` не изменено ни одной строки, менялись тест,
`build/iso/report.py`, копия workflow в `docs/ci/` и документы.

**Чего нет.** Двух строк `set -o pipefail` в живом workflow — до этого шаг «Result matrix»
по-прежнему зелёный при упавшем отчёте. Локального ISO и локальной загрузки. Исправленная матрица ещё ни разу не
напечаталась в настоящем прогоне — увидим в следующем `iso`. Артефакт ISO из CI я не скачивал и не
проверял `xorriso`. На живом железе — по-прежнему ничего.

## 2026-08-28 — Sheets: в ячейку теперь можно печатать, и это проверено живым движком

**Сделано.** Ввод с клавиатуры: набор поверх ячейки заменяет её (как в Excel), F2 правит на месте,
Enter фиксирует и уходит вниз, Escape отменяет, Delete очищает, стрелки и Tab ходят по сетке.
Строка формул перестала быть надписью — это редактор, Enter в ней уходит в движок. Всё через
`Workbook.set_input`: **что набрано — число, текст или формула — решает Calc, а не мы.**

**Впервые движок проверен по-настоящему.** В этой песочнице стоят `libreoffice-calc-nogui` и
`python3-uno`, и мост UNO заработал под интерпретатором 3.13: тесты движка Sheets больше не
пропускаются, а действительно поднимают headless LibreOffice 7.4.7 [dpkg, 2026-08-28]. Новые
тесты: `=A1+A2` считается движком, очищенная ячейка становится пустой (а не нулём), в строке
формул формула, в сетке результат.

Гейты: apps/sheets 15 passed (было 12, и раньше движковая часть пропускалась).

## 2026-08-28 — Zaldros Slides: PowerPoint-окно на живом движке Impress (ADR-0022)

**Сделано.** `apps/slides`: мост к Impress по UNO (слайды, макеты, заполнители, заметки, переходы,
PPTX/ODP, экспорт PDF), модель Qt и окно с лентой, панелью слайдов, полем заметок и строкой
состояния. **Первое офисное приложение, проверенное на живом движке**: тесты создают колоду, пишут
PPTX, открывают её заново и экспортируют настоящий PDF.

**Три вещи, которые сказал работающий движок, а не документация.**
- Заметки опознаются по `getShapeType()`, потому что `supportsService("…NotesShape")` возвращает
  False на той самой фигуре, у которой тип — ровно эта строка.
- Переход — это `TransitionType`; свойства `FadeEffect` у страницы в Impress 7.4 нет вовсе.
- Фильтр PPTX **не переносит переход** (и меняет номер макета). Это записано отдельным тестом,
  чтобы никто не заявил обратного.

Гейты: apps/slides 15 passed (движок настоящий), apps/sheets 15 passed, apps/writer 9 passed +
6 skipped (Writer'а в песочнице нет).

**Чего нет.** Режима докладчика и показа слайдов, анимаций, тем, вставки картинок и таблиц,
правки текста прямо на слайде.

## 2026-08-28 — С железа возвращается архив, и Alt+Tab перестал хвалить сам себя (ADR-0023)

**Повод.** Владелец усомнился: «эти скрины не настоящие, при реальной сборке может быть другой
интерфейс». Я скачал кадры из веток `ci-logs-boot-*` и посмотрел их. Кадры настоящие: это
screendump QEMU с загруженного ISO (ядро `7.0.0-30-generic`, 787 МБ RAM, 33 процесса) — рабочий
стол с нашим «Проводником», меню «Пуск» с закреплёнными приложениями, окно Dolphin.

**Но сомнение окупилось.** `alt_tab-held.png` и `alt_tab-after.png` оказались побайтово
одинаковыми (md5 `a4880e3e48`), а отчёт всё равно писал `switcher_visible: true`: сравнивался
только кадр «до» с кадром «с зажатым Alt», а смену окна этот кадр уже содержал. Теперь
`alt_tab_verdict` берёт три сравнения, оверлей считается увиденным только если кадр отличается от
обоих соседей, появилось поле `held_equals_after`, а PASS шага означает ровно то, что нужно
пользователю: окно сменилось (на кадрах — наш «Проводник» → Dolphin). Логика вынесена в чистую
функцию и покрыта тестами на настоящих числах того прогона.

**Канал с железа.** `tools/collect-logs.sh` едет в образе как `/usr/local/bin/zaldros-collect-logs`:
один запуск — один `.tar.gz` (журналы загрузки и сессии, `dmesg`, упавшие юниты, висящие jobs,
`systemd-analyze`, процессы, сокеты Wayland, состояние выходов DRM, CPU/PCI/USB/диски/сеть/звук/ввод,
Secure Boot, скриншот) плюс `35-backend-status.json` — снимок `tray()` с этой машины, где у каждого
показания источник и причина пустоты. Секретов не собирает (список запрещённого проверяется тестом),
без сети, ни один зонд не роняет запуск. Тест **запускает скрипт** на хосте без systemd, D-Bus, PCI
и экрана — он обязан выйти с нулём и дать читаемый архив. Инструкция для владельца — в `INSTALL.md`
(Rufus в режиме DD, Secure Boot off, `nomodeset` для Optimus, куда девать архив).

**Гейты.** shell 449 passed + 1 skipped (было 441), tools 44. CI на предыдущем коммите впервые за
семь коммитов зелёный (прогон 33160067325). Кадров до/после нет: под `zaldros_shell/` не изменено
ни строки.

**Чего нет.** Ни одного запуска на живом железе — архива с ноутбука пока не существует. Почему
оверлей переключателя не попал в кадр (не рисуется вовсе или исчезает быстрее 1.2 с) — не выяснено;
следующий прогон `iso` скажет это честно. Двух строк `set -o pipefail` в живом workflow всё ещё нет.

## 2026-08-28 — Пустой зонд — тоже не ответ (доработка ADR-0023)

CI покраснел на моём же коммите: `test_collect_logs.py` требовал, чтобы файл
`14-systemd-failed.txt` был непустым, а на раннере с настоящим systemd и без упавших юнитов
`systemctl --failed` печатает ровно ничего. Тест мерил хост — ровно то, за что ADR-0021 ругает
предыдущий тест; в песочнице (нет systemctl → «[missing tool]») он проходил.

Исправлено там, где была настоящая проблема: пустой файл в архиве двусмысленен для читателя, и
теперь `grab` пишет `[no output from: <команда>]`, если зонд не сказал ничего. Тест ужесточён — ни
один файл в архиве не может быть нулевого размера — и добавлен независимый от хоста тест: заглушка
`systemctl`, которая молча выходит с нулём, обязана попасть в архив как «молчала».
## 2026-08-28 — Командная строка по снимку, и привычные названия приложений

**Одна полоса вместо двух.** На присланном снимке настоящей командной строки вкладка, «+» и
стрелка профилей стоят **в заголовке окна**, рядом с кнопками управления. У нас было два ряда:
заголовок «Терминал» и под ним своя полоса вкладок. Теперь вкладки живут в `AppWindow` (`tabs`
стали живыми: клик, закрытие, «+», стрелка), а приложение рисует только сетку. Окно называется
«Командная строка».

**Приветствие — наше.** Две строки над приглашением: название системы из `/etc/os-release` и
версия ядра из `platform.release()`, затем «(c) Проект Zaldros. Свободное ПО, лицензия GPL-3.0.»
Версия Windows не копируется: это была бы и ложь о том, что запущено, и чужое имя в чужих словах.
Приветствие пишется в **наш** экран, а не в оболочку, — скрипт, читающий вывод, получает только
байты оболочки.

**Ошибка, которую нашло это приветствие.** Первая строка исчезала, едва окно принимало свой
настоящий размер. Причина: при уменьшении числа строк экран сбрасывал верхние строки в
scrollback. Теперь, как в xterm, сначала убираются **пустые строки под курсором**, и только
непустые уходят вверх. Это чинит не только приветствие, а любое уменьшение окна.

**Названия.** По просьбе: приложения зовутся привычно — Word, Excel, PowerPoint, «Командная
строка». Внутренние имена пакетов не трогал, чтобы не ломать импорты.

Гейты: shell 449 passed + 1 skipped, соответствие Windows 11 41/41. Кадры: «Пуск» изменился
ожидаемо (плитка переименована), остальные шесть — только часы.
