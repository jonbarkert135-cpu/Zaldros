# Iteration report 0006 — visual foundation

Format per spec PART 1 §16. Date: 2026-08-23.

**CURRENT OBJECTIVE** — Stop extending the backend; build a Windows-11-like visual foundation:
taskbar, Start, tray, quick settings, window decorations, context menus, design tokens — and make
real applications launch from it.

**RESEARCH** — Surveyed the open-source Windows-like field (Winux/Wubuntu/Linuxfx, Win11OS-kde,
Win11-icon-theme, OnzeMenuKDE / menu-11-next / Menu-11-Enhanced, tiledmenu, Zorin, AnduinOS, Plasma)
and audited every licence into `docs/VISUAL_THIRD_PARTY.md`. Two findings changed the plan:
Microsoft publishes **Fluent UI System Icons under MIT** and **Selawik, an OFL-licensed Segoe UI
replacement**. That is a legally clean route to a native-feeling Windows look. Geometry was taken
from Microsoft's own published metrics (24 px taskbar icons, 32 px Start pins).

**DECISION** — Reuse the heavy machinery (KWin, Plasma stack, Dolphin, Konsole) but write the shell
ourselves. The existing "Windows 11 KDE" projects are themes over Plasma: they change appearance,
not behaviour, and their artwork provenance is unverified. Adopting them would import exactly the
legal risk PART 1 §2 forbids. Reasoning recorded in `docs/VISUAL_THIRD_PARTY.md` §3.

**IMPLEMENTATION**
- Full design-token system (`qml/ZaldrosTheme/Theme.qml`): background / surface / surface-elevated /
  border / accent / text-primary / secondary / disabled / hover / pressed / selected, plus a
  typography scale and motion durations, in **dark and light**.
- Taskbar rebuilt to Windows 11 metrics: 48 px bar, 40 px buttons, 24 px icons, centred group,
  search pill, running indicator that widens when active, system tray with overflow chevron,
  two-line clock, notification button.
- Start rebuilt at 640 × 726 with 32 px padding: search field, pinned 6-column grid with 32 px icons,
  Recommended section, "Все приложения" list, footer with the real user name and memory, power
  button, and arrow-key/Enter keyboard navigation.
- New: quick settings flyout, Windows-11-style context menu, window decorations (rounded corners,
  32 px title bar, minimise/maximise/close with red close hover, active/inactive states).
- New backends: `desktop_entries.py` — real XDG `.desktop` discovery, localized names, field-code
  stripping, detached launching; `system.py` — battery, backlight, network, volume, Bluetooth read
  from sysfs / wpctl.
- Applied the **ponytail** skill: the hand-written .desktop parser was replaced by stdlib
  `configparser` (`strict=False`), cutting the parser roughly in half with the tests unchanged.

**TEST** — 32 shell tests (was 9) + 44 tool tests = **76 green**. New visual regression tests assert
measured pixels, not just that a file appeared: the 48 px taskbar band exists and differs from the
desktop, the centre group and tray zones contain drawn content, opening Start changes the frame, the
Start panel interior is uniform (no content ghosting), quick settings changes only the right side,
the context menu appears where it was opened, and the light theme is measurably lighter.

**RESULT** — Six evidence renders committed: desktop, Start (ru and en), quick settings, context
menu, light theme. Applications on this machine really launch from Start.

**PROBLEMS** — Sandbox has no battery, no audio server, no network interface up, no backlight — so
every quick-settings readout renders as unavailable. That is the correct behaviour under our
no-fake-data rule, and it also means **the quick settings have never been seen in their working
state**. Still no compositor: the taskbar is a window, decorations are a design, blur is faked with
a solid base.

**FIX** — Start ghosting (translucent panel over windows) fixed with an opaque base layer; taskbar
tile colours fixed (a QML gradient was resolving `parent.color` to black); pinned grid rows aligned
by fixed offsets instead of a centred column.

**METRICS** — 76 tests green. Visual scores (`docs/VISUAL_SCORE.md`): taskbar 4.0, Start 4.0, tray
3.7, quick settings 3.7, decorations 3.7, context menus 3.8, desktop 3.5. Parity: 0 COMPLETE,
6 PARTIAL, 5 PROTOTYPE, 2 BACKEND ONLY, 19 MISSING.

**NEXT** — 1) layer-shell panel on KWin so the taskbar is a real panel; 2) window tracking and
taskbar state from the compositor; 3) Alt+Tab, minimise/maximise/close wired to real windows;
4) search index (apps → settings → files); 5) vendor Fluent icons + Selawik once the build host has
network; 6) first VM boot.
