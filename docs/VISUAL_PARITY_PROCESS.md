# Windows 11 visual parity: how it is measured

Zaldros aims at a Windows 11-like operating system experience, not a Windows-themed Linux. "Looks
close" is not a result here, so the shell's geometry is measured against Windows 11 and checked by
a tool on every run.

## The loop

    REFERENCE → IMPLEMENTATION → SCREENSHOT → PIXEL COMPARE → FIX → RETEST

1. **REFERENCE** — `tools/visual/measure_reference.py` measures a real Windows 11 capture pixel by
   pixel and writes logical (100 % scale) values to `system/theme/win11-reference.json`.
   `--check` re-measures and fails when the committed numbers drift from the screenshot.
2. **IMPLEMENTATION** — `shell/zaldros-shell/qml/ZaldrosTheme/Theme.qml` holds the tokens the
   components use. Nothing in the QML carries a magic number that is not in the reference.
3. **SCREENSHOT** — `tools/visual/parity.py` renders the shell offscreen in seven states
   (desktop, Start, search, quick settings, notifications, context menu, Settings focused).
4. **PIXEL COMPARE** — the same tool reads the geometry of every named component back out of the
   live scene graph and compares it with the reference, one metric at a time.
5. **FIX / RETEST** — `python3 tools/visual/parity.py` prints a PASS/FAIL line per metric and exits
   non-zero on any drift. `tests/test_visual_parity.py` runs the same comparison in CI.

Evidence lands in `docs/visual/current/`: the seven frames, one crop per component in
`components/`, and `parity-report.json`.

## Sources

| Area | Capture | Committed? |
| --- | --- | --- |
| Start, taskbar rhythm | `assets/refs/win11_start_reference.png`, 1920x1280 at 125 % | yes |
| Desktop taskbar, Explorer, Settings, notification centre, context menu | maintainer's own screenshots, 2026-08-26, 125 % | no — they show a personal desktop, so only the measurements were kept |

Every value in `win11-reference.json` is a measurement. Where a capture could not settle a value it
is absent rather than guessed.

## Current state (cycle 1, 2026-08-26)

29 of 29 metric checks match the reference: taskbar height, button pitch, centring, tray margin;
Start size, padding, search field, pin cell grid, footer; window title bar and caption buttons;
Explorer tab strip, navigation bar, command bar and sidebar; Settings rail; quick settings and
notification centre width and edge gap; context menu width and stack height.

## What parity does not yet cover

- Colour and blur: the checks are geometric. Acrylic and Mica are approximated with flat tints
  because the headless renderer has no live blur; only a compositor run can prove those.
- Motion: durations are set from the reference theme (75 ms hover), but nothing measures them.
- Iconography: system glyphs are Fluent UI System Icons (Microsoft, MIT). Application icons come
  from the host icon theme, so a machine without one still shows lettered tiles.
- Typography: Selawik (Microsoft, SIL OFL 1.1) is metric-compatible with Segoe UI and legal to
  ship. Segoe UI itself is not redistributable and is never bundled.
