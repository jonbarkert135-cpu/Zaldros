# Research 02 — Desktop architecture, compositor and toolkit

Requirement: spec PART 1 §3, §9, §10 and PART 2 (the whole Windows-like desktop surface).

## What the desktop must deliver (PART 2)

Taskbar with previews and grouping, Start menu, global search, real system tray (StatusNotifierItem),
quick settings that drive real subsystems, notification centre with history and DND, snap layouts,
Alt+Tab, virtual desktops, multi-monitor with per-monitor scaling, clipboard history, screenshots,
recycle bin, accessibility, theming.

## Options

| Option | Cost to reach PART 2 parity | Performance | Risk |
|---|---|---|---|
| **A. KDE Plasma 6 (KWin) + Zaldros shell layer** | Low — snapping, tray (SNI), quick settings, notifications, multi-monitor, a11y, Wayland session all exist and are mature | Good; Plasma 6 idles well below GNOME on comparable hardware and is far more configurable | Low; risk is "looks like a theme" — mitigated by owning our own applets/shell components |
| B. GNOME + extensions | Medium-high | Medium | High: extension API breaks every release; Windows workflows fight GNOME's design |
| C. Custom shell on **smithay** (Rust) | Very high — years; must implement layer-shell, xwayland, session, input, a11y | Potentially best | Very high; COSMIC (smithay) took a full team years |
| D. Custom shell on **wlroots** (C) | High | Very good | High; wlroots is mature and C-based, but everything above the compositor is still ours |

Evidence: Wubuntu and the "Windows Modern for KDE Plasma 6" theme pack both reach a convincing
Windows-11 desktop on Plasma, i.e. Plasma's architecture does not obstruct Windows workflows.
Smithay is a real production base (COSMIC, niri) but is a compositor *building-block* library — Xfce's
Wayland compositor chose it precisely because it is low-level and fully customisable, and their
roadmap is measured in years.

## Decision (two-stage, deliberate)

**Stage 1 (Phase 1–3): Option A.** Zaldros Desktop = KWin (Wayland) + our own shell components:
Zaldros Taskbar, Zaldros Start, Zaldros Quick Settings, Zaldros Search, Zaldros Settings — implemented
as first-class Plasma/Qt 6 + QML components in our repo, not as downloaded themes. Plasma supplies the
compositor, session, tray protocol, notifications daemon and a11y stack; we supply the shell UX.

**Stage 2 (evaluated at end of Phase 3, only if measurements justify it):** replace `plasma-shell`
with a standalone Zaldros shell process talking directly to KWin via layer-shell, keeping KWin.
A full compositor rewrite (C/D) is explicitly **out of scope** unless Stage 2 measurements prove KWin
itself is the bottleneck.

**Toolkit: Qt 6 + QML for shell and system apps.** Reasons: KWin/Plasma integration, mature Wayland
support, GPU-accelerated scene graph, one toolkit for shell *and* apps (spec §18 forbids mixed visual
systems), and RAM/CPU profile far below Electron. Rust GUI stacks (iced/slint) and GTK4 are rejected as
the primary shell toolkit — GTK4 would fight KWin/Plasma integration, and Rust GUI toolkits lack the
accessibility and Wayland-shell maturity PART 2 §20 requires. Rust *is* the preferred language for
non-GUI system components (daemons, tooling) where it competes with C.

## Windows compatibility layer

Wine + Proton (via a managed prefix manager) as an installable component, not a core dependency;
never bundle Microsoft binaries or fonts. Segoe UI is proprietary — the Zaldros design system ships
an open substitute (Inter / Selawik) and, optionally, imports fonts from a Windows installation the
user already licenses.
