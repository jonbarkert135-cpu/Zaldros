# Visual component matrix

Where each visible piece of Zaldros comes from, what it is made of, and how far it is from Windows
11. "Source" is the *origin of the design or asset*; "Implementation" is what actually runs.
Status: **COMPLETE / PARTIAL / PROTOTYPE / MISSING**. A high visual score never implies function.

| Component | Source | Implementation | Stack | Status | Visual score | Real behaviour today |
| --- | --- | --- | --- | --- | --- | --- |
| System icons | Fluent UI System Icons (MIT) | vendored SVG, recoloured per theme | SVG + Qt | **COMPLETE** | 5.0 | 90 glyphs, both themes, HiDPI |
| UI font | PT Sans (OFL 1.1) | vendored TTF, registered at startup + fontconfig alias | TTF | **COMPLETE** | 5.0 | closest measured match to Segoe UI Cyrillic; installed system-wide so KWin/Dolphin match |
| Design tokens | ours, informed by Win11-gtk-theme values | `ZaldrosTheme/Theme.qml` | QML | **COMPLETE** | 4.5 | dark + light, one source of truth |
| Taskbar | ours; behaviour ref. sfwbar | `Taskbar.qml` | QML | PROTOTYPE | 4.3 | real clock, real running-app state; still a window, not a panel |
| Start menu | ours; behaviour ref. Menu11 / menu-11-next | `StartMenu.qml` | QML | PARTIAL | 4.3 | launches real applications, keyboard navigation |
| System tray | ours | `TrayButton.qml` + Fluent glyphs | QML | PARTIAL | 4.0 | real presence detection, no per-icon backends |
| Quick settings | ours | `QuickSettings.qml` | QML | PARTIAL | 4.0 | real readouts; toggles read-only |
| Context menus | ours | `ContextMenu.qml` | QML | PROTOTYPE | 4.0 | opaque, correct metrics; items do nothing yet |
| Window decorations | ours; KWin will draw the real ones | `AppWindow.qml` | QML | PROTOTYPE | 4.0 | 32 px title bar, 46 px caption buttons, Fluent glyphs |
| Desktop icons | ours + Fluent glyphs | `Shell.qml` | QML | PROTOTYPE | 3.8 | not interactive |
| Wallpaper | **ours** — generated artwork | `assets/wallpaper/generate.py` | Qt painter | **COMPLETE** | 4.5 | 3840×2160 render, reproducible from source |
| Application icons | host icon theme, then vendored Fluent-icon-theme (GPL-3) | `icons.py` `_app_icon` + `assets/icons/apps/` | SVG | **PARTIAL** | 4.5 | colour icons always render; lettered tile only for unknown apps |
| System icon theme | **ours** — built from `assets/icons/` | `/usr/share/icons/Zaldros` | SVG theme | **COMPLETE** | 4.3 | 17 apps, 9 places, 90 glyphs; unknown names fall back to the lettered tile |
| Cursor theme | Fluent-icon-theme cursors (GPL-3) — the only borrowed pack | `/usr/share/icons/Fluent-dark-cursors` + `default` alias | Xcursor | **COMPLETE** | 4.5 | 111 shapes, set for KDE, GTK, GNOME schemas and the session env |
| GTK app styling | **ours** — tokens over stock Adwaita | `gtk.css` in `/etc/skel` | GTK3/4 | PARTIAL | 3.0 | colour and font match the shell; chrome is Adwaita, not Fluent |
| Window titlebars (real apps) | placeholder | borderless Breeze via `kwinrc` | KWin | PROTOTYPE | 2.5 | our own Aurorae theme not written yet |
| Search | ours | field only | QML | MISSING | 3.0 | no index |
| Explorer | Dolphin fork planned | window mock | — | MISSING | 2.0 | nothing real |
| Settings | ours (Zaldros backend) | — | — | MISSING | 0 | — |
| Notifications | ours | — | — | MISSING | 0 | — |
| Login screen / SDDM | ours | — | — | MISSING | 0 | — |
| Boot splash | Plymouth (AnduinOS pattern) | — | — | MISSING | 0 | — |
| Installer | Ubiquity/Calamares (AnduinOS pattern) | — | — | MISSING | 0 | — |

**Backend, never borrowed** (spec §12): Zaldros services, settings backend, application management,
update system, hardware services, compatibility registry — `tools/` and `shell/zaldros-shell/`.

## Comparison against Windows 11, component by component

| Windows 11 | Zaldros now | Gap that matters most |
| --- | --- | --- |
| Desktop | icons + wallpaper, correct proportions | no selection, no drag, no desktop context actions |
| Taskbar | centred group, running indicator, tray, clock | not a layer-shell panel; no real window list |
| Start | pins, all-apps, user, power | no search results, no Recommended feed |
| Search | field only | no index at all — the single biggest UX gap |
| Explorer | mock window | needs the Dolphin fork |
| Settings | — | nothing yet |
| Context menus | correct metrics and order | no actions |
| Notifications | — | nothing yet |
| Quick settings | correct layout, honest readouts | toggles not wired |
| Window decorations | correct metrics | KWin integration missing |
