# ADR-0002 — Compositor: KWin 6 (Wayland)

Status: accepted.
Context: PART 2 requires snapping, tray (StatusNotifierItem), per-monitor scaling, virtual desktops,
Alt+Tab, accessibility and a full Wayland session — all mature in KWin.
Decision: use KWin as the compositor; do not write a compositor.
Alternatives: smithay (COSMIC-class effort, years), wlroots (C, still everything above it is ours),
Mutter/GNOME (extension API instability, workflow mismatch).
Consequences: we inherit KWin's release cadence (pin per release, CI against next version); our
differentiation must live in our own shell components, not in themes.
