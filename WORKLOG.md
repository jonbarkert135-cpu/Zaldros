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
