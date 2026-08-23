# Visual license audit

Every third-party visual asset that is **shipped** with Zaldros, with the licence terms that govern
it. Zaldros itself is GPL-3.0-or-later, which is compatible with everything listed here.
Anything not on this list is not shipped. Reference-only projects are in
`docs/VISUAL_FOUNDATION_RESEARCH.md`.

## 1. Vendored today (in the repository, in use by the shell)

| Asset | Path | Upstream | Version / date | Licence | Copyright | Modify | Redistribute | Attribution | Derivative-work duty |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Fluent UI System Icons (26 SVGs) | `assets/icons/fluent/` | github.com/microsoft/fluentui-system-icons | fetched 2026-08-23 | **MIT** | © 2020 Microsoft Corporation | yes | yes | keep the MIT text (`assets/icons/fluent/LICENSE`) | none — permissive |
| Selawik (5 faces) | `assets/fonts/selawik/` | github.com/microsoft/Selawik | 1.01 | **SIL OFL 1.1** | © 2015 Microsoft, Reserved Font Name **Selawik** | yes | yes, incl. bundling | ship `LICENSE.txt` | **must rename** any modified face; may not be sold on its own |
| Application icons (18 SVGs) | `assets/icons/apps/` | github.com/vinceliuice/Fluent-icon-theme | fetched 2026-08-23 | **GPL-3.0** | © vinceliuice and contributors | yes | yes | ship `COPYING` + `AUTHORS` (both vendored) | publish modifications; offer source |
| Wallpaper | `assets/wallpaper/` | **ours** (`generate.py`) | 2026-08-23 | GPL-3.0 (Zaldros) | Zaldros project | — | — | — | — |
| GPL-3.0 licence text | `LICENSE` | gnu.org | 3, 29 June 2007 | — | FSF | verbatim only | yes | — | — |

Recolouring the icons at runtime (`shell/zaldros-shell/zaldros_shell/icons.py`) is a permitted
modification under MIT; no icon file is altered on disk.

## 2. Approved for the next integration step (audited, not yet vendored)

| Asset | Upstream | Licence | Conditions we must meet |
| --- | --- | --- | --- |
| Full mime/device icon theme | vinceliuice/Fluent-icon-theme | GPL-3.0 | app icons already vendored; the complete theme follows with the ISO |
| Cursor theme | vinceliuice/Fluent-icon-theme (`cursors/`) | GPL-3.0 | same |
| App / mime icons (alternative) | yeyushengfan258/Win11-icon-theme | GPL-3.0, derived from Ubuntu **Yaru** | ship COPYING + `AUTHORS` credit to Yaru |
| GTK application theme | yeyushengfan258/Win11-gtk-theme | GPL-3.0 | ship COPYING; if we patch the SCSS, publish the patch |

## 3. Explicitly rejected

| Asset | Reason |
| --- | --- |
| Winux / Wubuntu / Linuxfx themes and PowerTools | proprietary, paid, redistribution not granted; 2022 activation-database leak |
| Any Windows 11 icon, font, sound, wallpaper or cursor extracted from a Windows installation | Microsoft proprietary assets — spec PART 1 §2 and §13 of this cycle |
| Segoe UI itself | proprietary Microsoft font (Selawik exists precisely as its metric-compatible substitute) |
| The four-pane Windows logo and the name "Windows" | Microsoft trademarks — Zaldros uses its own mark |
| Zorin OS themes | Zorin trademark and mixed Pro licensing |

## 4. Obligations Zaldros carries

1. `THIRD_PARTY_LICENSES.md` lists every component, version, source, licence and modification.
2. Licence files travel with the assets in the same directory — never stripped by the build.
3. GPL-3 components: the ISO ships an offer of source, and our patches are published in this repo.
4. Selawik keeps its reserved name; if we ever hint a face, it is renamed first.
5. Trademarks (Windows, Fluent, Selawik, Yaru, Zorin) are acknowledged as their owners' marks and
   are never used to suggest endorsement.
