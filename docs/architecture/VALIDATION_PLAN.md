# Validation cycle — BUILD → BOOT → RUN → MEASURE → COMPARE

Status of every number in this document: **not measured yet.** The pipeline below exists and is
syntax-checked, but nothing has been built or booted, because the environment I run in has no root,
no `/dev/kvm`, no QEMU and no way to install packages. Marked throughout as:

> `BLOCKED — ENVIRONMENT LIMITATION: agent sandbox is an unprivileged container (uid≠0, no /dev/kvm,
> no package installation). ISO building needs debootstrap+chroot (root) and booting needs QEMU.`

The pipeline therefore runs in GitHub Actions (`docs/ci/iso.yml` → `.github/workflows/iso.yml`).

## What runs

| Stage | Script | Evidence produced |
| --- | --- | --- |
| BUILD | `build/iso/build-iso.sh <variant>` | a UEFI-bootable live ISO per variant |
| BOOT | `build/iso/boot-test.sh <iso> <profile>` | serial log, QMP screenshot, exit code |
| RUN + MEASURE | `build/iso/selftest.py` inside the guest | one JSON line on `/dev/ttyS0` |
| COMPARE | `build/iso/report.py` | PASS/FAIL matrix in the job summary |

**A successful build is not a boot test.** `boot-test.sh` reports PASS only if the guest's self-test
marker appears on the serial log; a clean QEMU exit without that marker is recorded as FAIL together
with the last 4000 characters of serial output.

## The three architectures under test

| Variant | Session command | Packages beyond the base image | Disk cost |
| --- | --- | --- | --- |
| 1 `full` — proposed Plasma-shell architecture | `startplasma-wayland` | `plasma-desktop`, `plasma-workspace-wayland` | **+900 MiB, +552 packages** |
| 2 `services` — KWin + Plasma services, **no plasmashell** | `kwin_wayland -- python3 -m zaldros_shell` | `plasma-workspace-wayland`, `plasma-nm`, `plasma-pa`, `powerdevil`, `kscreen` | **+686 MiB, +376 packages** |
| 3 `legacy` — LayerShell-Qt only | same, without the Plasma services | `kwin-wayland`, `layer-shell-qt`, QtQuick | **+355 MiB, +291 packages** |

Disk figures are **real**, computed from the Ubuntu `resolute` package index on 2026-08-23 by walking
the full `Depends`/`Pre-Depends` closure over a common base image (338 packages, 1380 MiB).
They are the only measured numbers in this cycle.

## Answer to the critical question — KWin without plasmashell

**Yes, and variant 2 is exactly that test.** Facts behind it:

- `kwin-wayland` does **not** depend on `plasma-workspace`; it depends on `kwin-common`,
  `kwayland-integration`, `xwayland` and KF6 libraries. `plasmashell` is a separate binary shipped in
  `plasma-workspace` — installing the package does not mean running the process.
- Which means the Plasma pieces we actually want can be started individually as normal user services:
  `kwin_wayland` (compositor), `powerdevil` (power/backlight), `kscreen`/`kded6` (displays),
  `plasma-nm`/`plasma-pa` (network/audio backends), `polkit-kde-agent-1`, `kglobalacceld` — with our
  shell as the only shell process and **no plasmashell, no plasma containments, no Plasma desktop**.
- The cost of doing so is small on disk (686 vs 900 MiB) and, in theory, large in RAM, since
  `plasmashell` is the single biggest desktop process in third-party measurements. Whether that theory
  holds for *our* image is precisely what the boot matrix must show.

If variant 2 boots and gives Windows-11 behaviour at materially lower RAM than variant 1, ADR-0008
should be **MODIFIED** to "KWin + selected Plasma services + Zaldros shell" rather than "Plasma shell
package".

## Base-image finding that changes an earlier decision

Ubuntu **24.04 LTS ships Plasma 5.27 / Qt 5** — KWin 6 is simply not there. Plasma 6 arrives in
Ubuntu **26.04 LTS (`resolute`): KWin 6.6.4, layer-shell-qt 6.6.4, Qt 6.10**.
Everything in ADR-0002/0003 assumes KWin 6, so the base must be 26.04 LTS, not 24.04.
[archive.ubuntu.com package indices, 2026-08-23]

## Hardware profiles

| Profile | vCPU | RAM | Graphics |
| --- | --- | --- | --- |
| low | 2 | 4 GiB | `-vga std`, software rendering (llvmpipe) |
| mid | 4 | 8 GiB | virtio-gpu |
| modern | 8 | 16 GiB | virtio-gpu |

## Known limitations of this harness (declared, not hidden)

- `BLOCKED — ENVIRONMENT LIMITATION`: **battery impact** cannot be measured in a VM; needs hardware.
- `BLOCKED — ENVIRONMENT LIMITATION`: **GPU usage** in QEMU measures virtio-gpu/llvmpipe, not a real
  driver; only relative, never absolute.
- `BLOCKED — ENVIRONMENT LIMITATION`: if a runner exposes no `/dev/kvm`, boots fall back to TCG
  emulation, and **boot-time numbers become meaningless** (RAM and process counts stay valid).
- **UI responsiveness** and **Start launch time** are not yet instrumented: they need input injection
  into the guest. Planned next, deliberately not faked now.
- Visual regression against the Windows 11 reference still comes from the offscreen render tests, not
  from the VM screenshot, until the screenshot path is proven to capture a composited desktop.

## Stage 2 — UI validation ("booted" is not "responsive")

Booting proves nothing about feel, so every image is driven through the full interaction chain on at
least the LOW and MID profiles: **BOOT → LOGIN → DESKTOP → START OPEN → START CLOSE → APP LAUNCH →
WINDOW OPEN → WINDOW MOVE → MINIMIZE → RESTORE → ALT+TAB → TASKBAR RESPONSE → EXPLORER OPEN.**

The test has two halves that never pretend to be one:

| Half | Script | Measures | Method |
| --- | --- | --- | --- |
| guest | `build/iso/uitest.py` | desktop ready, Explorer open, window move, minimise, restore | KWin's own scripting D-Bus interface — works under full Plasma *and* bare `kwin_wayland`, so all three variants run the identical test |
| host | `build/iso/ui-drive.py` | Start open/close, Alt+Tab, taskbar click | QEMU QMP `input-send-event` injects real keys and clicks; `screendump` captures the composited screen before and after |

A host step is PASS **only if the screen actually changed** — a keypress that produces no visible
change is a FAIL, not a pass. Every step also records the CPU% and RSS of `kwin_wayland`,
`plasmashell` and the shell during that step, which is our CPU/RAM spike measure.

Artifacts per run: serial log, stage-1 JSON, stage-2 guest JSON, stage-2 host JSON, and a
before/after screenshot pair for every driven step.

### Honest limits of stage 2

- `BLOCKED — ENVIRONMENT LIMITATION`: **frame/render stability** is not measured. Under QEMU the
  frames come from llvmpipe or virtio-gpu, so frame timings would grade the emulator, not KWin. Real
  frame pacing needs hardware.
- Screen-change detection is a coarse pixel signature, not a visual diff: it proves *something*
  happened, not that the right thing happened. The screenshots are kept so a human (and the visual
  scoring in `docs/VISUAL_SCORE.md`) can judge the "right thing" part.
- Input latency is measured as key-injection → visible change, which includes QEMU's own latency and
  is therefore comparable between variants but not an absolute figure.

## Decision rubric — per architecture, after stage 2

Each variant gets ACCEPT / MODIFY / REJECT judged on five axes together, never on RAM alone:

| Axis | Source |
| --- | --- |
| Performance | stage-1 RAM, process count, boot time; stage-2 CPU/RAM spikes |
| UI responsiveness | stage-2 step timings, LOW profile weighted heaviest |
| Visual fidelity | `docs/VISUAL_SCORE.md` and the screenshot pairs |
| Hardware compatibility | boot PASS/FAIL across profiles, `-vga std` (llvmpipe) included |
| Complexity | package closure size and the amount of Zaldros-specific code the variant needs |

**Design is never traded for a benchmark.** A variant that wins on RAM or CPU while degrading Start,
taskbar, Explorer, Settings, animations, decorations, typography, icons, spacing, colours or
Windows-like behaviour is REJECTED on that ground alone.

## Rule for this cycle

No optimisation may degrade Start, taskbar, Explorer, Settings, animations, decorations, typography,
icons, spacing, colours or Windows-like behaviour. An optimisation that saves RAM and costs
appearance is **rejected**, and the render tests in `shell/zaldros-shell/tests/test_render.py` are the
gate that detects it.
