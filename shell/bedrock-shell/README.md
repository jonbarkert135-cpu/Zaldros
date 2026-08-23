# Bedrock Shell (prototype)

The Windows-11-like desktop shell: taskbar, Start, system tray, quick settings, context menus and
window decorations. Qt 6 / QML with a Python backend.

## Run

    QT_QPA_PLATFORM=offscreen python -m bedrock_shell render --out desktop.png
    python -m bedrock_shell render --start | --quick | --context | --light | --locale en
    python -m bedrock_shell run            # needs a display

## Tests

    python -m pytest tests -q     # 32 tests: backends, .desktop parsing, system readouts, renders

## Layout

| Path | What |
| --- | --- |
| `bedrock_shell/desktop_entries.py` | real XDG `.desktop` discovery, parsing, launching |
| `bedrock_shell/system.py` | battery / backlight / network / volume / Bluetooth readouts |
| `bedrock_shell/backend.py` | clock, `/proc` process list, memory |
| `bedrock_shell/model.py` | Qt models exposed to QML |
| `qml/BedrockTheme/Theme.qml` | design tokens (dark + light), typography, motion |
| `qml/` | Taskbar, StartMenu, QuickSettings, ContextMenu, AppWindow, SysIcon |
| `data/pinned.json` | Bedrock's default pin set (installed state is computed at runtime) |

## Rules this code follows

1. **No fake system data.** A value that cannot be measured renders as unavailable with the reason.
2. **No Microsoft assets.** Geometry follows published Windows metrics; artwork is ours.
3. **Every visual claim has a render test.** Screenshots in `docs/evidence/` come from the code.

## Known limitations

Runs as a window, not a Wayland layer-shell panel. No window tracking, no search index, quick-setting
toggles are read-only, icons are placeholder strokes until Fluent (MIT) is vendored.
