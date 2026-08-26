# ADR-0011 — The UI font is chosen by coverage first, metrics second

**Status:** accepted, 2026-08-26. Amends ADR-0007, which picked Selawik.

## Context
ADR-0007 vendored Selawik because Microsoft published it under the OFL as a *metric-compatible*
substitute for Segoe UI. Metric compatibility was the only property we checked.

Selawik's cmap has 383 glyphs and **no Cyrillic at all**. Zaldros ships a Russian interface, so
every label in the shell — the whole Settings tree, the Start menu, the taskbar — was rendered by
whatever fontconfig offered instead, which on our ISO is `fonts-dejavu-core`. The shell reported
"Selawik" while the screen showed DejaVu Sans: wide, heavy and unmistakably not Windows. The
maintainer spotted it in a shipped screenshot; no test could, because nothing tested the font
against the text we actually draw.

## Decision
1. **Coverage is a precondition, not a preference.** The shell accepts a family only if it
   registered *and* reports Cyrillic coverage (`app.load_fonts`), otherwise it prints the fallback
   it fell back to instead of claiming a family it does not have.
2. **PT Sans (ParaType, SIL OFL 1.1) is the UI font.** Chosen by measurement, not taste:
   `tools/visual/font_match.py` crops real Segoe UI Cyrillic from `assets/refs/win11_start_reference.png`
   and ranks candidates by pixel difference at matched ink height.

   | Font | Body text vs Segoe | Heading vs Segoe Semibold | Width ratio |
   | --- | --- | --- | --- |
   | **PT Sans** | **62.0 %** | **31.6 %** (Bold) | 1.01 / 0.99 |
   | Noto Sans | 65.5 % | 75.8 % | 1.00 |
   | Open Sans | 95.2 % | 70.3 % | 1.03 |
   | IBM Plex Sans | 99.6 % | 72.2 % | 1.06 |
   | Inter | 106.9 % | 89.0 % | 1.11 |
   | DejaVu Sans (what shipped) | 93.0 % | 80.3 % | 1.11 |

   Absolute numbers include hinting differences; the ranking is the result. PT Sans also matches
   Selawik's Segoe metrics most closely of all candidates (5.4 % mean advance-width deviation,
   identical x-height 500/1000 and cap height 700/1000), so the geometry tokens measured for Segoe
   still hold.
3. **The font is installed system-wide**, not only inside the shell: `/usr/share/fonts/truetype/zaldros`
   plus a fontconfig alias mapping `sans-serif`, `system-ui`, `Segoe UI` and `Selawik` to PT Sans,
   so KWin decorations, Dolphin and Konsole stop drawing in DejaVu too.
4. **Selawik is removed** rather than kept as a Latin fallback. Two families in one interface means
   Latin and Cyrillic words in the same sentence render in different designs.

## Consequences
- PT Sans has no 600 weight, so `Font.DemiBold` resolves to Bold. That is the pairing measured
  above and it lands within 1 % of Segoe UI Semibold, so it stands until a Cyrillic UI face with a
  real semibold appears under an OFL-compatible licence.
- `tests/test_ui_font.py` fails if a shipped face cannot draw any character used in the shell
  sources, if the shell and the system theme name different families, or if the font is not
  installed system-wide. The Selawik class of bug cannot return silently.
- Any future font swap must re-run `tools/visual/font_match.py` and beat the numbers above.
