# Iteration 0009 — first green boot (run #18, b17846d)

CURRENT OBJECTIVE: prove Zaldros boots and runs, then compare the three architectures.

RESULT: `iso` run 32671131899 — **12/12 jobs success**. 3 ISO builds + 9 boot jobs
(variant x profile) all reached a running desktop and passed the guest self-test:
kernel 7.0.0-30-generic, systemd, Wayland socket, KWin, Zaldros session unit, real
application launch (konsole, 2.0 s), zero failed units.

## variant x profile (QEMU/OVMF, llvmpipe — NOT hardware evidence)

| variant | profile | selftest | idle RAM | proc | wall s | KWin | plasmashell | app launch | UI (guest) | Start/taskbar (host input) |
|---|---|---|---|---|---|---|---|---|---|---|
| full | low | PASS | 883 MiB | 39 | 207 | yes | yes | PASS 2.0 s | 5/5 PASS | Start open PASS 1.51 s, close PASS, taskbar PASS, Alt+Tab FAIL |
| full | mid | PASS | 911 MiB | 39 | 208 | yes | yes | PASS 2.0 s | 5/5 PASS | same |
| full | modern | PASS | 971 MiB | 39 | 210 | yes | yes | PASS 2.0 s | 5/5 PASS | same |
| services | low | PASS | 452 MiB | 22 | 204 | yes | no | PASS 2.0 s | 4/5 (restore FAIL) | all FAIL |
| services | mid | PASS | 479 MiB | 22 | 207 | yes | no | PASS 2.0 s | 4/5 (restore FAIL) | all FAIL |
| services | modern | PASS | 541 MiB | 22 | 209 | yes | no | PASS 2.0 s | 4/5 (restore FAIL) | all FAIL |
| legacy | low | PASS | 468 MiB | 22 | 207 | yes | no | PASS 2.0 s | 4/5 (restore FAIL) | all FAIL |
| legacy | mid | PASS | 480 MiB | 22 | 205 | yes | no | PASS 2.0 s | 4/5 (restore FAIL) | all FAIL |
| legacy | modern | PASS | 522 MiB | 22 | 208 | yes | no | PASS 2.0 s | 4/5 (restore FAIL) | all FAIL |

Top RSS, full/low: plasmashell 391 MiB, kwin_wayland 242, kded6 144, polkit-kde-auth 138,
kaccess 129, ksmserver 128. services/legacy: kwin_wayland 181-189, everything else < 34 MiB.
`wall_seconds` ~205-210 is the harness ceiling, not boot time — boot time is still not measured
(`boot_time` empty, systemd-analyze unavailable in the live session): **BLOCKED — needs a
timestamp probe in the self-test.**

## VISUAL GATE
- full: screenshot shows a rendered desktop with panel, clock, tray, launcher — but it is
  *stock Plasma* (default Breeze wallpaper, left-aligned taskbar). Windows 11 theming from the
  visual-foundation cycle is **not applied in the ISO yet**.
- services / legacy: screenshot is a fully black 1280x800 frame. KWin runs, Dolphin launches and
  can be moved/minimised, but **nothing is painted on screen** — the Zaldros shell process exists
  yet renders no panel and no wallpaper. Restore FAIL and every host-input step FAIL are downstream
  of that.

## VERDICT
- **full — ACCEPT (provisional)**: only variant with a visible, interactive desktop. Cost: ~430 MiB
  extra RAM and 17 extra processes, of which plasmashell alone is 391 MiB.
- **services — MODIFY**: the cheap architecture we actually want (452 MiB / 22 proc, half the RAM),
  but it fails the visual gate today. Not rejected: the defect is our shell, not the architecture.
- **legacy — MODIFY**: indistinguishable from services in every metric (+16 MiB); no reason to keep
  it as a separate variant unless it diverges later.

Architecture stays **PROPOSED**. Per the owner's rule, an option that degrades Start/taskbar/visuals
cannot be accepted for its RAM number — so the next cycle is to make the Zaldros shell actually
render under `services`, then re-run and re-compare.

NEXT
1. Root-cause the black screen: capture the shell's stderr/journal into the boot artifacts.
2. Make the Zaldros shell paint wallpaper + taskbar via LayerShell under `services`.
3. Measure real boot time (kernel + userspace timestamps) in the self-test.
4. Fix Alt+Tab (host QMP key injection produced no screen change even on full).
5. Apply the Windows 11 theme/icon foundation inside the ISO, then re-shoot the visual comparison.
