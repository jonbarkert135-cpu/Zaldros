# Iteration report 0007 — open-source visual foundation

Format per spec PART 1 §16. Date: 2026-08-23.

**CURRENT OBJECTIVE** — Stop hand-drawing a Windows-like look. Research the real open-source
projects, audit their licences, and integrate the best legally usable parts into the running shell.

**RESEARCH** — The sandbox gained network access this cycle, so every project was **cloned and read
locally**, not judged from its README: Win11-gtk-theme, Win11-icon-theme, AnduinOS, plus about
fifteen more (Fluent-icon-theme, Fluent-kde, KDE-Windows-Modern, Win11OS-kde, willow-theme,
OnzeMenuKDE, Menu11, menu-11-next, tiledmenu, sfwbar, wayle, win2xcur, Zorin, Winux). Full table in
`docs/VISUAL_FOUNDATION_RESEARCH.md`. Three findings changed the plan:

1. **Microsoft publishes usable assets.** Selawik (OFL 1.1) is a metric-compatible Segoe UI
   substitute and Fluent UI System Icons is MIT. Both are Microsoft-authored — the closest legal
   approximation of the Windows look that exists.
2. **Win11-icon-theme's provenance is clean** — its `AUTHORS` names Ubuntu's Yaru as the source. The
   previous cycle rejected it as "unverified"; that judgement was wrong and is corrected here.
3. **AnduinOS builds its ISO with plain debootstrap + squashfs + xorriso** (61 chroot mods,
   Ubiquity installer). No container runtime, no bootc — meaning our image can be built on an
   ordinary CI runner. This directly attacks the "no bootable image yet" blocker.

Honest counter-finding: Win11-gtk-theme is a **Material Design engine wearing a Windows skin**
(ripples, Material elevation z1–z24). Adopting it wholesale would have made Zaldros look like
Material. Only measured values were taken.

**DECISION** (ADR-0007) — Vendor Microsoft's permissive assets; reuse GPL-3 theme work slot by slot
(icons, cursors, GTK styling); keep writing our own Qt/QML shell because theme packs change looks,
not behaviour; follow AnduinOS's build path. Never ship extracted Microsoft assets or anything from
Winux/Linuxfx.

**IMPLEMENTATION**
- Vendored `assets/fonts/selawik/` (5 faces + OFL) and `assets/icons/fluent/` (26 SVGs + MIT).
- `zaldros_shell/icons.py`: a QML image provider that recolours Fluent SVGs to the current theme
  colour, and serves real application icons from the host icon theme by freedesktop name.
- `SysIcon.qml` rewritten from ~120 lines of hand-drawn Canvas paths to a 20-line Image.
- `AppTile.qml`: real themed app icon when one exists, lettered tile otherwise, Fluent glyph for the
  shell's own desktop entries.
- Font registered at startup; the shell reports the family it actually got.
- `LICENSE` now carries the full GPL-3.0 text; `THIRD_PARTY_LICENSES.md` records the vendored assets.
- Adopted the 75 ms hover timing measured in Win11-gtk-theme; kept our colours and radii.
- Four new documents: `VISUAL_FOUNDATION_RESEARCH.md`, `VISUAL_LICENSE_AUDIT.md`,
  `ZALDROS_DESIGN_SYSTEM.md`, `VISUAL_COMPONENT_MATRIX.md`.

**TEST** — 40 shell tests + 44 tool tests = **84 green**. New `tests/test_icons.py` asserts the
icons render in the requested colour in both themes, that every glyph the QML asks for is vendored,
and that unknown glyphs/apps return nothing instead of a wrong icon. New render tests assert the
tray and desktop icons contain lit pixels, and that the context menu is opaque.

**RESULT** — Evidence renders regenerated (`docs/evidence/`), with `before-*.png` kept for the
before/after comparison. Icons and font are visibly Microsoft-grade; the desktop, tray, Start,
window buttons, quick settings and context menu all use them.

**PROBLEMS** — First integration rendered **every icon blank**. Cause: QML URL-encodes the provider
id, so the colour arrived as `%23ffffff` and the SVG recolour produced an invalid fill. Render tests
did not catch it because a blank icon still renders "fine". Second defect: the context menu was
translucent enough to read the window text behind it.

**FIX** — `unquote()` the provider id; opaque base rectangle under the menu's acrylic tint. Both are
now covered by tests that check **pixels**, not just that a frame was produced.

**METRICS** — 84 tests green. Visual scores: taskbar 4.5, Start 4.3, context menus 4.3, tray 4.2,
quick settings 4.2, desktop 4.0, decorations 4.0 (icons and typography now score 5.0).
Vendored assets: 26 icons, 5 font faces. `SysIcon.qml`: 120 → 20 lines.

**NEXT** — 1) build a real ISO the AnduinOS way and boot it; 2) layer-shell taskbar panel on KWin;
3) window tracking + Alt+Tab; 4) vendor Fluent-icon-theme app icons and cursors; 5) search index;
6) wire quick-settings toggles.
