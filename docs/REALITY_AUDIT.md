# Reality audit — 2026-08-23

Ordered by the owner: *"не защищай текущую реализацию — найди всё, чего не хватает"*. The audit was
run before any new feature work, and the conclusion is that the criticism was correct.

## 1. Verdict in one line

**Before this iteration the project was DOCUMENTATION + BACKEND ONLY.** There was no shell, no
desktop, no window, no image, no boot — nothing a user could look at. Four command-line tools and a
large document set are useful groundwork, but they are not an operating system, and calling that
"progress toward a Windows-like OS" would have been dishonest.

## 2. Component classification

Legend: REAL / PROTOTYPE / BACKEND ONLY / DOCUMENTATION ONLY / MOCK / NOT IMPLEMENTED.

| Component | Before audit | After this iteration | Evidence |
| --- | --- | --- | --- |
| Zaldros Shell | NOT IMPLEMENTED | **PROTOTYPE** | renders offscreen, 9 tests, `docs/evidence/*.png` |
| Taskbar | NOT IMPLEMENTED | **PROTOTYPE** | real clock, real running-process underline |
| Start menu | NOT IMPLEMENTED | **PROTOTYPE** | pinned grid, animated open/close, click-outside dismiss |
| Search | DOCUMENTATION ONLY | DOCUMENTATION ONLY (UI shell only, no index) | — |
| Explorer | DOCUMENTATION ONLY | DOCUMENTATION ONLY | — |
| Settings | DOCUMENTATION ONLY | DOCUMENTATION ONLY | — |
| Terminal / PowerShell | DOCUMENTATION ONLY | DOCUMENTATION ONLY | decision only (reuse Konsole) |
| Task Manager | BACKEND ONLY | BACKEND ONLY | `zaldros-sysprobe` service/resource map |
| Device Manager | BACKEND ONLY | BACKEND ONLY | `zaldros-hwinfo` real `/proc`+`/sys` inventory |
| Update Center | DOCUMENTATION ONLY | DOCUMENTATION ONLY | — |
| Installer | DOCUMENTATION ONLY | DOCUMENTATION ONLY | contract in `INSTALL.md` |
| Recovery | DOCUMENTATION ONLY | DOCUMENTATION ONLY | contract in `RECOVERY.md` |
| Notifications | NOT IMPLEMENTED | NOT IMPLEMENTED | — |
| Networking / audio / Bluetooth | NOT IMPLEMENTED | NOT IMPLEMENTED | component choices only |
| Graphics / multi-monitor | NOT IMPLEMENTED | NOT IMPLEMENTED | never run on a GPU |
| Application installation | NOT IMPLEMENTED | NOT IMPLEMENTED | — |
| Bootable image | NOT IMPLEMENTED | NOT IMPLEMENTED | Containerfiles written, never built |
| Performance harness | REAL | REAL | `zaldros-bench`, 13 tests |
| Compatibility registry | REAL (backend) | REAL (backend) | evidence gate fails unproven claims |

## 3. Real run — what was actually executed

| Attempted | Result |
| --- | --- |
| Unit tests (4 tools) | **44 passed** |
| Shell backend + render tests | **9 passed** (PySide6 6.11.2, offscreen) |
| Shell rendered to PNG, RU and EN | **succeeded** — `docs/evidence/shell-desktop-ru.png`, `shell-start-ru.png`, `shell-desktop-en.png` |
| `zaldros-bench collect` live | succeeded, but boot metrics `null` — no systemd here |
| `zaldros-sysprobe` / `zaldros-hwinfo` live | run, output is honest but nearly empty in a container |
| Container image build | **impossible** — no `podman`/`docker` |
| VM boot, GPU/multi-monitor/hardware profiles | **impossible** — no `qemu`, no `/dev/kvm` |
| Comparison vs Ubuntu/Mint/Fedora/Debian VMs | **impossible** — same blocker |

Everything in the "impossible" rows is therefore **untested**, and no compatibility or performance
claim is made about them. This is the single blocker that matters; it now depends on the GitHub
Actions runner (the `image` job the owner added) or a real Linux machine.

## 4. Self-critique

### 10 strengths
1. Architecture decisions are written down with evidence and revisable (ADR-0001…0005).
2. The evidence gate makes an unproven compatibility claim fail the build — rare discipline.
3. `zaldros-bench` cannot report a false optimisation win (missing metric ⇒ INCONCLUSIVE).
4. Real system data everywhere: `/proc`, `/sys`, no fixtures pretending to be hardware.
5. 53 tests total, all green, no external dependencies in the tools.
6. Full spec preserved verbatim, with contradictions resolved explicitly rather than silently.
7. The shell prototype renders and is visually regression-tested, not mocked in Figma.
8. Localization was designed in before the first UI string existed.
9. Honest feature matrix — nothing is claimed as working that has not run.
10. Licensing and naming risks were caught before public release, not after.

### 10 weaknesses
1. No bootable image exists; the OS has never started.
2. The shell is a window, not a Wayland session — the hard part (layer-shell, KWin integration) is untouched.
3. Zero hardware evidence records; the hardware matrix is entirely `untested`.
4. Zero performance baselines on a real system.
5. Too much documentation relative to running code — the audit's core finding.
6. Pinned apps are placeholder JSON, not parsed `.desktop` files.
7. No notifications, no quick settings, no window management, no Alt+Tab.
8. No installer code at all.
9. No accessibility work has started.
10. The base-distribution decision is still open, which blocks image work.

### 10 missing features (highest value first)
1. Layer-shell integration so the taskbar is a real panel, not a window.
2. Real application launching (`.desktop` parsing + exec + window tracking).
3. Window list from the compositor, so the taskbar shows actual windows.
4. Working search (apps first, files later).
5. Notifications and a quick-settings flyout.
6. Explorer (file browsing at all).
7. Settings with at least display, network, sound and accounts.
8. Bootable image and installer.
9. Multi-monitor handling.
10. Session start-up: login → shell autostart.

### 10 technical risks
1. No build host ⇒ nothing verifiable end to end. (Highest.)
2. Layer-shell/KWin integration may force C++ and a plugin, not just QML.
3. NVIDIA + Wayland regressions on user hardware.
4. Reskinned Plasma components drift with every KDE release.
5. Scope: 15 system applications is years of work.
6. Fake-looking prototypes creating an illusion of progress — mitigated by this audit's honesty rules.
7. Immutable base vs. users expecting to install anything system-wide.
8. Qt/QML performance on very weak GPUs (the Legacy profile target) is unmeasured.
9. Translation debt if strings are added without `tr()`.
10. Single-maintainer bus factor.

### 10 UX gaps vs Windows 11
1. No window snapping / snap layouts. 2. No Alt+Tab or task view. 3. No right-click context menus.
4. No notification centre or calendar flyout. 5. No quick settings (Wi-Fi/volume/brightness).
6. No file manager. 7. No Run dialog (Win+R). 8. No clipboard history (Win+V). 9. No screenshot tool
binding (Win+Shift+S). 10. No file associations or "Open with".

## 5. Fixes applied in this cycle

- Built the first **vertical slice** of the desktop: taskbar + Start, running from real system data.
- Added render-based visual tests so UI claims are backed by an actual frame.
- Wrote `docs/WINDOWS_ZALDROS_PARITY.md` (per-feature parity, all statuses evidence-based) and
  `docs/FEATURE_RESEARCH.md` (what to take from Ubuntu, Mint, Debian, Arch, Fedora, KDE, GNOME).
- Recorded the audit itself, including the parts that are unflattering.

## 6. Next 6 tasks, in priority order

1. Confirm the GitHub Actions `image` job builds a container image — first real build evidence.
2. Decide the base distribution with the test defined in `docs/research/03-base-distribution-reopened.md`.
3. Make the taskbar a real layer-shell panel on KWin instead of a window.
4. Parse `.desktop` files and actually launch applications from Start.
5. Track real windows from the compositor and show them in the taskbar.
6. Boot an image in a VM and capture the first screenshot of Zaldros running for real.
