# ADR-0003 — Shell and application toolkit: Qt 6 / QML

Status: accepted.
Context: one visual system for shell and system apps (PART 2 §18), low RAM/CPU (PART 1 §6),
KWin/Plasma integration, accessibility.
Decision: Qt 6 + QML for shell and system applications; Rust for new non-GUI daemons and tooling;
C++ where Qt/KWin APIs require it.
Alternatives: GTK4 (fights Plasma integration), Electron/web (memory cost incompatible with goals),
Rust GUI toolkits (immature Wayland-shell and a11y support today).
Consequences: contributors need Qt/QML skills; theming is unified through a single Zaldros design system.
