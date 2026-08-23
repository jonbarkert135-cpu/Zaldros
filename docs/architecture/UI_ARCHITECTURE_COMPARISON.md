# UI architecture comparison — what gets us closest to Windows 11

Question: *should Zaldros keep its own Qt 6 / QML shell, or is another toolkit / desktop architecture
objectively better for a maximally faithful Windows 11 experience on Linux?*

Scored 1–5 on **Visual fidelity · UX fidelity · Performance · Hardware compatibility · Development
complexity** (5 = best; for complexity 5 = cheapest). Evidence is named; where a number could not be
measured on our own hardware it is marked as a third-party figure, not as our result.

## The options

| # | Architecture | What it means concretely |
| --- | --- | --- |
| A | Own Qt 6/QML shell, standalone (**today**) | our process draws taskbar/Start; KWin composites |
| B | Own Qt 6/QML shell **as a Plasma shell package** | `org.zaldros.desktop` containment + applets run inside plasmashell |
| C | Plasma with themes and applets (Winux/KDE-Windows-Modern route) | stock Plasma panel + Win11 theme + third-party menu applet |
| D | GNOME + extensions (AnduinOS/Zorin route) | Dash-to-Panel + ArcMenu + Blur-my-Shell + GTK theme |
| E | GTK4 shell (gtk4-layer-shell, Rust/C) | rewrite the shell in GTK4 to match the GTK theme |
| F | Own shell on a small toolkit (Quickshell / LayerShell-Qt / eww) | QML or CSS-driven bar frameworks on wlr-layer-shell |
| G | Hybrid: KWin + Plasma **services**, our shell UI | our UI, Plasma's window/tray/power backends |

## Scores

| Option | Visual | UX | Perf | HW compat | Dev cost | Total | The decisive fact |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A — standalone QML shell | 4 | 2 | 5 | 4 | 2 | 17 | we must write window management, tray protocol, session, power ourselves — years of work already solved elsewhere |
| **B — QML shell as a Plasma shell package** | **5** | **5** | **3** | **5** | **4** | **22** | Plasma's own form factors (Bigscreen, Nano, Mobile) prove the mechanism: replace the shell package, keep every backend |
| C — themed stock Plasma | 3 | 4 | 3 | 5 | 5 | 20 | a theme cannot change *layout logic*; Winux still reads as Plasma with a skin, and its Start applet is a third-party plasmoid |
| D — GNOME + extensions | 3 | 3 | 3 | 5 | 5 | 19 | AnduinOS itself ships fixes for a race between `blur-my-shell` and `dash-to-panel`; the ceiling is the extensions' |
| E — GTK4 rewrite | 4 | 3 | 4 | 4 | 1 | 16 | throws away our shell for a toolkit with weaker window-management APIs; libadwaita fights non-GNOME layouts |
| F — Quickshell / LayerShell-Qt only | 4 | 3 | 5 | 4 | 3 | 19 | great for a bar, but still no tray/session/power stack; the same gap as A with less of our own code |
| G — hybrid (our UI + Plasma services) | 5 | 4 | 4 | 5 | 3 | 21 | technically the same as B minus plasmashell's applet machinery; a fallback if B proves too heavy |

## Evidence behind the numbers

- **Performance.** Third-party idle measurements put Plasma 6 at roughly 700–800 MB on a clean
  install, with `plasmashell` ~655 MB RSS and `kwin_wayland` ~305 MB in one 2026 review; a
  cross-desktop table ranks Plasma highest of the mainstream desktops. GNOME lands slightly lower,
  XFCE/LXQt far lower. **We have measured none of this ourselves** — the sandbox has no compositor.
  Zaldros must reproduce these numbers on its own images before treating them as fact.
- **Windows-11 fidelity in practice.** Every existing "Windows-like" distro is a themed stock
  desktop: Winux = Plasma + theme + paid PowerTools, AnduinOS/Zorin = GNOME + extensions. None of
  them reproduces Windows 11 *behaviour* (Start search, snap layouts, taskbar grouping semantics);
  they reproduce its colours.
- **Shell replacement is a supported Plasma feature.** `plasma-bigscreen` and `plasma-nano` ship
  their own shell packages and are launched with `PLASMA_DEFAULT_SHELL=…`. That is the officially
  supported path to "our layout, their infrastructure".
- **Layer-shell for Qt exists** (`LayerShell-Qt`, used by Plasma itself; Quickshell for QML on
  `wlr-layer-shell`), so a QML panel can be a real Wayland panel — the gap that makes option A's UX
  score low is not a toolkit limitation, it is unfinished work.
- **GTK cannot host our shell.** The GTK theme styles *applications*; it contains no taskbar, Start,
  tray or window list (its `src/` ships styles for gnome-shell, cinnamon, xfwm4, plank — other
  people's shells). Rewriting in GTK4 would buy visual consistency with GTK apps that we already get
  by shipping the GTK theme, and would cost us Qt's window-management stack.

## Answer 1 — which architecture

> **Option B: keep Qt 6 / QML, and turn the Zaldros shell into a Plasma shell package running on
> KWin.**

Reasoning in one line each:
1. **Visual fidelity is not the bottleneck** — with Selawik, Fluent icons and the Win11 theme packs
   we already render Windows-11-grade pixels. Behaviour is the bottleneck.
2. **Behaviour is what Plasma gives away for free**: `libtaskmanager` (real window list, grouping,
   activation), StatusNotifier tray, KWin effects and rules, KScreen, PowerDevil, NetworkManagerQt,
   session and lock. Writing those ourselves is the multi-year trap option A is walking into.
3. **The shell package mechanism is designed for exactly our case** — a different desktop layout on
   the same stack, shipped as `org.zaldros.desktop`.
4. **Toolkit switching buys nothing**: GTK gives worse window APIs, and both toolkits render the same
   pixels. The cost of E is the highest of all options for the smallest visual gain.
5. **Performance risk is real but manageable**: Plasma's overhead is largely plasmashell + KWin. Our
   "Zaldros Legacy" profile can drop plasmashell and run the same QML through LayerShell-Qt
   (option F/G) on weak machines — one codebase, two runtimes.

Rejected: C and D because their ceiling is someone else's layout logic; E because it is the most
expensive option with no fidelity gain; A as an end state, though it remains the prototype we build
from.

## Answer 2 — what to keep and what to replace

| Part of Zaldros today | Verdict |
| --- | --- |
| `tools/` (sysprobe, hwinfo, compat registry, bench) | **keep** — pure Python, no UI coupling |
| `zaldros_shell/` backends (.desktop discovery, launching, `/proc`, sysfs readouts) | **keep**, but replace the sysfs/`wpctl` readouts with PowerDevil/NetworkManagerQt/PipeWire APIs as they arrive |
| `qml/ZaldrosTheme/Theme.qml` design tokens | **keep** — becomes the shell package's theme |
| `qml/` Taskbar, Start, tray, quick settings, context menus | **port**, not rewrite: same QML becomes a containment + applets |
| `qml/AppWindow.qml` (fake window chrome) | **delete** — KWin + the Aurorae/Breeze decoration draws real windows |
| Explorer mock inside the shell | **delete** — Dolphin fork with the Win11 icon theme |
| Own icon/glyph drawing | **already deleted** — theme icons win, vendored set is the fallback |
| `system/theme/*` integration scripts | **keep and extend** with the Plasma look-and-feel package |
| `render` CLI + pixel tests | **keep** — this is our only visual regression net |
| ADR-0002 (KWin), ADR-0003 (Qt/QML) | **confirmed** by this analysis |
| ADR-0001 (Fedora bootc) | **superseded** — Ubuntu base with AnduinOS-style live-build |

## What this costs

- Learning `plasma-framework` / KF6 applet APIs and packaging `org.zaldros.desktop`: the main risk.
- A dependency on plasma-workspace in the default profile — measurable RAM cost we must benchmark.
- The current standalone entry point stays as the development harness (it is what renders our test
  screenshots), so nothing is thrown away in the transition.
- Estimated: the port of the existing QML into a containment + three applets is days, not months,
  because the visual layer is already token-driven and backend-separated.

## What must be proven before this is final

1. Build an image and boot it (AnduinOS-style live-build) — until then every performance claim here
   is someone else's number.
2. Measure `plasmashell` + `kwin_wayland` RSS and boot time on our own image, on two machines.
3. Prototype `org.zaldros.desktop` with the taskbar containment only, and confirm the real window
   list, tray and activation work through Plasma's backends.
