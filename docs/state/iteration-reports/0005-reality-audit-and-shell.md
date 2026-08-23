# Iteration report 0005 — reality audit and the first desktop vertical slice

Format per spec PART 1 §16. Date: 2026-08-23.

**CURRENT OBJECTIVE** — Audit the project honestly against its own goal (a Windows-11-like desktop OS,
not a toolbox), then immediately fix the biggest gap the audit finds.

**RESEARCH** — Classified every component in the repository. Result: Shell, Taskbar, Start, Explorer,
Settings, notifications, networking, audio, Bluetooth, graphics, multi-monitor and application
installation were all NOT IMPLEMENTED or DOCUMENTATION ONLY; only the four CLI tools were real. The
owner's suspicion — that the project had drifted into backend and documentation — was correct.

**DECISION** — Stop adding utilities. Build the first vertical slice of the actual desktop, and make
it produce *visual evidence* that can be tested, since PART 5 §8 asks for visual regression testing.

**IMPLEMENTATION** — `shell/zaldros-shell`: Qt 6/QML Zaldros Taskbar and Start menu with the Windows 11
layout (centred group, search pill, tray with time above date, pinned grid, animated Start).
Backend in Python: locale-aware clock, running-application detection from the real `/proc` table, real
memory pressure. Notable engineering detail: QML context properties are invisible to types loaded
through a `qmldir` module, which silently produced `null` backends; the theme singleton was moved into
its own `ZaldrosTheme` module and the backend objects are now injected explicitly from `Shell.qml`.

**TEST** — 9 new tests: pinned-data integrity, real-process reading, locale clock formats (ru/en_US/de),
memory percent is real-or-None, plus render tests that assert the frame is 1280×800, that a dark
taskbar band is actually drawn at the bottom, that opening Start changes the rendered centre pixel, and
that a bad output path fails loudly instead of silently.

**RESULT** — `9 passed`, tool suite still `44 passed`. Three evidence screenshots committed:
`docs/evidence/shell-desktop-ru.png`, `shell-start-ru.png`, `shell-desktop-en.png`. This is the first
time anything in the project has been *looked at* rather than described.

**PROBLEMS** — (1) The shell is a window, not a Wayland layer-shell panel: it is not yet a desktop
session. (2) Nothing launches from it. (3) The taskbar reflects processes, not real windows.
(4) Still no image build, no VM boot, no hardware or performance evidence — no `podman`, no `/dev/kvm`.
Every hardware-profile and cross-distro benchmark requested in the audit prompt is therefore
**not done**, and is recorded as not done rather than approximated.

**FIX** — Added a `shell` job to CI that installs Qt, runs the tests and uploads the rendered
screenshots as artifacts, so UI regressions are caught on every push.

**METRICS** — 53 tests green. Parity: 0 COMPLETE, 3 PARTIAL, 3 PROTOTYPE, 2 BACKEND ONLY, 21 MISSING.
Evidence records: 0. Performance baselines: 0.

**NEXT** — 1) confirm the CI `image` job builds; 2) settle the base distribution by that build test;
3) layer-shell panel on KWin; 4) `.desktop` parsing and real application launching; 5) real window
list; 6) first VM boot screenshot.
