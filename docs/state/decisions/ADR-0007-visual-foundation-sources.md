# ADR-0007 — Where the Windows-like visuals come from

**Status:** accepted, 2026-08-23. Supersedes the "build every visual from scratch" stance of
iteration 0006.

## Context
The owner asked us to stop hand-drawing a Windows-like look and to reuse the best open-source work
where licences allow. All candidate projects were cloned and inspected
(`docs/VISUAL_FOUNDATION_RESEARCH.md`).

## Decision
1. **Vendor Microsoft's own permissively licensed assets**: Selawik (OFL 1.1) and Fluent UI System
   Icons (MIT). This is the closest legal approximation of the Windows look and needs no reverse
   engineering.
2. **Reuse GPL-3 theme work per slot, not wholesale**: Fluent-icon-theme for app/mime icons and
   cursors, Win11-gtk-theme for GTK application styling.
3. **Keep writing our own shell** in Qt 6/QML: theme packs change appearance, not behaviour, and we
   need real window management, launching and system state.
4. **Follow AnduinOS's build approach** (debootstrap → squashfs → xorriso, Ubiquity installer)
   instead of the container-image route, which the sandbox and normal CI cannot run.
5. **Never** ship extracted Microsoft assets, Segoe UI, the Windows logo, or anything from
   Winux/Wubuntu/Linuxfx.

## Consequences
- Typography and iconography jumped from "own strokes" to Microsoft-authored assets in one cycle.
- Zaldros stays GPL-3.0-or-later, which is compatible with every reused component.
- We owe attribution and source offers for the GPL-3 components; tracked in
  `THIRD_PARTY_LICENSES.md` and `docs/VISUAL_LICENSE_AUDIT.md`.
- ADR-0001 (Fedora bootc base) is now clearly superseded in practice: the build path is Ubuntu-based
  live-build tooling.
