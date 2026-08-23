# ADR-0008 — Shell runtime: Plasma shell package on KWin

**Status:** proposed (2026-08-23), pending the two measurements listed below.

## Context
The owner asked whether the Qt 6/QML architecture should survive at all, given that the Windows-11
theme packs cannot style our shell. Full comparison of seven options:
`docs/architecture/UI_ARCHITECTURE_COMPARISON.md`.

## Decision
Keep Qt 6 / QML. Stop shipping the shell as a standalone application and ship it as a **Plasma shell
package** (`org.zaldros.desktop`) running on KWin, reusing `libtaskmanager`, the StatusNotifier
tray, PowerDevil, KScreen and NetworkManagerQt for behaviour, while our QML defines the entire
layout and look. Keep a LayerShell-Qt-only runtime of the same QML for the "Zaldros Legacy"
low-end profile.

## Alternatives rejected
- Themed stock Plasma (Winux route) and GNOME + extensions (AnduinOS/Zorin route): the ceiling is
  someone else's layout logic; both reproduce Windows' colours, not its behaviour.
- GTK4 rewrite: highest cost, no fidelity gain, weaker window-management APIs.
- Standalone shell forever: forces us to reimplement tray, session, power and window management.

## Consequences
- `AppWindow.qml` (fake window chrome) and the Explorer mock leave the shell; KWin and a Dolphin
  fork take over.
- The default profile depends on plasma-workspace — a RAM cost that must be measured on our image.
- The current standalone entry point stays as the render/test harness.

## Conditions to accept
1. A Zaldros image that boots.
2. Measured `plasmashell` + `kwin_wayland` RSS and boot time on that image, on two machines,
   compared against the Legacy profile.
