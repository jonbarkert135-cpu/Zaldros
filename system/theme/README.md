# Zaldros visual layer — integration

The Windows-11 look is **installed, not coded**. Zaldros ships upstream theme packages and forces
them as system defaults; the shell only fills the gaps no theme can cover (taskbar behaviour, Start,
launching, system state).

## What runs, in order

| Step | Script | Result |
| --- | --- | --- |
| 1 | `fetch-sources.sh /usr/src` | clones Win11-gtk-theme, Win11-icon-theme, Fluent-icon-theme at pinned refs |
| 2 | `install-visual-theme.sh --dest <rootfs>` | runs the upstream installers, then writes the defaults below |
| 3 | image build | the rootfs ships with the themes already applied for every new user |

## What step 2 writes

| Path | Purpose |
| --- | --- |
| `/usr/share/themes/Win11-Dark`, `Win11-Light` | GTK 3/4 theme, rounded windows + blur tweaks |
| `/usr/share/icons/Win11`, `Win11-dark` | icon theme for every toolkit |
| `/etc/xdg/kdeglobals` | icon theme and colour scheme for Qt/KDE apps and the shell |
| `/etc/skel/.config/gtk-{3,4}.0/settings.ini` | per-user GTK defaults incl. Selawik and the cursor theme |
| `/usr/share/glib-2.0/schemas/90_zaldros-theme.gschema.override` | GNOME-schema defaults (portals, some apps) |
| `/etc/xdg/kwinrc` | blur + contrast effects, borderless maximised windows, Aurorae decoration |
| `/etc/zaldros/visual.conf` | the shell reads this: icon theme, cursor, font, taskbar alignment, corner radius |

## What a theme pack cannot do — and who covers it

| Requirement | Covered by |
| --- | --- |
| Window frames, buttons, menus, dialogs of **applications** | the GTK/Qt themes, exactly as upstream drew them |
| Icons everywhere | Win11 icon theme; the shell asks the theme by freedesktop name |
| Rounded corners, blur, borderless maximised windows | KWin config above |
| **Taskbar centred, Start, tray, quick settings, window list, launching** | the Zaldros shell — no theme pack contains these; a GTK theme is a stylesheet, it has no taskbar |
| Cursor | Fluent-icon-theme cursors |

The shell now takes its icons from the installed theme first and falls back to the vendored subset
only when the theme is missing (for example inside a build container), so on a real Zaldros system
every icon on screen comes from the theme package, not from our code.

## Verifying on a real system

```sh
sudo ./fetch-sources.sh /usr/src
sudo ./install-visual-theme.sh --dest / --variant dark
gsettings get org.gnome.desktop.interface gtk-theme     # 'Win11-Dark'
kreadconfig6 --file kdeglobals --group Icons --key Theme # Win11-dark
```
