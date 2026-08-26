# ADR-0012 — Alt+Tab is KWin's grab and our layout

**Status:** accepted, 2026-08-27. Follows ADR-0008 (no plasmashell).

## Context
Alt+Tab has failed in every booted ISO from run #27 onward, and each run blamed a different layer:

* run #27 — no global shortcut daemon in the image (`kglobalacceld` is a *recommend* of KWin);
* run #28 — the daemon was installed but lives under a multiarch libexec path, not `/usr/bin`;
* run #28b — the session started it, but the test pressed Alt+Tab while the shell was the only
  toplevel window, so there was nothing to switch to and the failure was the test's;
* run #29 — with `kglobalacceld` running and a second window (Dolphin) open, the key still changed
  nothing at all: `changed_fraction` 0.0.

The remaining explanation is the layout. KWin 6.6 ships exactly one window switcher,
`thumbnail_grid`, and its QML imports `org.kde.plasma.core`, `org.kde.ksvg`,
`org.kde.plasma.components` and `org.kde.kirigami`. A Zaldros session runs KWin with no Plasma
shell (ADR-0008), so the layout cannot load, and a switcher that cannot load shows nothing and
switches nothing. Pointing `LayoutName` at the KDE default was never going to work here.

## Decision
1. **KWin keeps the grab.** A Wayland client cannot take a global key; the compositor is the only
   process that can own Alt+Tab, so the shell does not try to. `kglobalshortcutsrc` still binds
   `Walk Through Windows` to KWin.
2. **The layout is ours.** `system/theme/tabbox/zaldros` is a `KWin/WindowSwitcher` package whose
   QML imports QtQuick and `org.kde.kwin` and nothing else. It draws the Windows 11 shape: the
   desktop dimmed behind a centred grid of live thumbnails, caption above each card, the current
   card outlined in the accent colour. Colours and the corner radius are substituted at install
   time from the same tokens as the colour scheme, so the switcher cannot drift from the desktop.
3. **The QML is tested here, not in the image.** `tests/test_switcher.py` renders the installed
   substitutions and loads the file against stubs of `TabBoxSwitcher` and `WindowThumbnail`, and
   checks every `model.<role>` against the role names in kwin v6.6.0's `ClientModel`. An ISO cycle
   is 45 minutes; a typo should cost seconds.

## Consequences
* One more file we own and must maintain against KWin's QML API. That API is small and stable
  (model, currentIndex, visible, screenGeometry) and the test pins the parts we use.
* **The switcher lists KWin toplevels, and the shell is one of them.** Explorer and Settings are
  QtQuick items *inside* the shell window, so Alt+Tab shows a single "Zaldros" entry for both
  instead of one card each. Windows shows them separately. Making them real toplevels is a
  separate change, tracked in WORKLOG; it is a shell architecture decision, not a theme one.
* Card proportions are provisional. Everything else in the desktop is measured against Windows 11
  captures; the switcher has no reference capture yet, so its cell size is shaped after the
  Windows 11 layout but not yet verified against it. It stays provisional until measured.
