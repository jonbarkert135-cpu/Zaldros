# Zaldros Shell (prototype)

The Windows-11-like desktop shell: taskbar, Start, system tray, quick settings, context menus and
window decorations. Qt 6 / QML with a Python backend.

## Run

From the repository root: `python3 tools/dev/setup.py shell`.
Then, from `shell/zaldros-shell`:

    QT_QPA_PLATFORM=offscreen ../../.venv/bin/python -m zaldros_shell render --out desktop.png
    ../../.venv/bin/python -m zaldros_shell run            # needs a display

The renderer also accepts `--start`, `--quick`, `--context`, `--light` and `--locale en`.
Profiles, host prerequisites and read-only environment checks:
[development setup](../../docs/development/SETUP.md).

## Tests

    QT_QPA_PLATFORM=offscreen ../../.venv/bin/python -m pytest tests -q

Current counts and exact evidence are in [project state](../../docs/state/PROJECT_STATE.md).
Local/private-bus/offscreen tests and real VM/system/hardware checks have distinct scopes.

## Layout

| Path | What |
| --- | --- |
| `zaldros_shell/desktop_entries.py` | real XDG `.desktop` discovery, parsing, launching |
| `zaldros_shell/system.py` | battery / backlight / network / volume / Bluetooth readouts |
| `zaldros_shell/backend.py` | clock, `/proc` process list, memory |
| `zaldros_shell/model.py` | Qt models exposed to QML |
| `qml/ZaldrosTheme/Theme.qml` | design tokens (dark + light), typography, motion |
| `qml/` | Taskbar, StartMenu, QuickSettings, ContextMenu, AppWindow, SysIcon |
| `data/pinned.json` | Zaldros's default pin set (installed state is computed at runtime) |

## Rules this code follows

1. **No fake system data.** A value that cannot be measured renders as unavailable with the reason.
2. **No Microsoft assets.** Geometry follows published Windows metrics; artwork is ours.
3. **Every visual claim has a render test.** Screenshots in `docs/evidence/` come from the code.

## Known limitations

The standalone entry point uses a QQuickView; internal QML app windows and external
KWin windows must be verified separately. Linux service adapters and writable controls
exist, but the synchronous GUI path, reconnect recovery, installed-system integration
and hardware acceptance remain incomplete. See the capability register rather than
inferring completeness from a render. Asset provenance/licensing gaps remain tracked.
