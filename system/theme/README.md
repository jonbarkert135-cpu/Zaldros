# Zaldros visual layer — integration

The look is **ours**. Zaldros installs exactly one third-party theme pack — the cursor theme — and
generates everything else from this repository (ADR-0010). The shell draws the taskbar, Start, tray,
quick settings and window chrome; the icon theme is assembled from `assets/icons/`.

## What runs, in order

| Step | Script | Result |
| --- | --- | --- |
| 1 | `fetch-sources.sh /usr/src` | sparse-clones `Fluent-icon-theme/cursors` at a pinned ref |
| 2 | `install-visual-theme.sh --dest <rootfs> --assets <repo>/assets` | installs the cursors, builds the `Zaldros` icon theme, writes the defaults below |
| 3 | image build | the rootfs ships with all of it applied for every new user |

## What step 2 writes

| Path | Purpose |
| --- | --- |
| `/usr/share/icons/Fluent-cursors`, `Fluent-dark-cursors` | the one borrowed pack, copied unmodified (GPL-3) |
| `/usr/share/icons/default/index.theme` | makes that pack the actual pointer — without it Xcursor ignores the setting |
| `/usr/share/icons/Zaldros` | our icon theme, built from `assets/icons/{apps,places,fluent}` |
| `/etc/xdg/kdeglobals` | icon theme and colour scheme for Qt/KDE apps and the shell |
| `/etc/xdg/kcminputrc` | cursor theme and size for KDE (kdeglobals is not read for this) |
| `/etc/skel/.config/gtk-{3,4}.0/settings.ini` + `gtk.css` | Adwaita plus our tokens, Selawik, our icons and cursor |
| `/usr/share/glib-2.0/schemas/90_zaldros-theme.gschema.override` | GNOME-schema defaults (portals, some apps) |
| `/etc/xdg/kwinrc` | blur + contrast effects, borderless maximised windows, borderless Breeze decoration, thumbnail-grid Alt+Tab |
| `/etc/xdg/kglobalshortcutsrc` | Alt+Tab, Meta+D and the snap/window shortcuts KWin registers at startup |
| `/etc/zaldros/visual.conf` | the shell reads this: icon theme, cursor, font, taskbar alignment, corner radius |
| `/usr/share/doc/zaldros/licenses/` | COPYING/AUTHORS for every GPL-3 asset in the image |

## Who covers what

| Requirement | Covered by |
| --- | --- |
| Taskbar, Start, tray, quick settings, window list, launching, context menus | the Zaldros shell — no theme pack contains behaviour |
| Icons | our `Zaldros` theme; the shell asks by freedesktop name and falls back to the vendored SVGs |
| Rounded corners, blur, borderless maximised windows | KWin config above |
| Pointer | Fluent-icon-theme cursors (GPL-3) — the only borrowed pack |
| GTK application chrome | stock Adwaita + our colour tokens. Colour parity only, tracked as a gap |
| Window titlebars | Breeze, borderless — placeholder until our own Aurorae theme exists |

## Verifying on a real system

```sh
sudo ./fetch-sources.sh /usr/src
sudo ./install-visual-theme.sh --dest / --assets /opt/zaldros/assets --variant dark
kreadconfig6 --file kdeglobals --group Icons --key Theme     # Zaldros
kreadconfig6 --file kcminputrc --group Mouse --key cursorTheme  # Fluent-dark-cursors
ls /usr/share/icons/Fluent-dark-cursors/cursors | wc -l      # 111 shapes
```

The in-guest self-test reports the same facts as `visual_layer` in its JSON, so a missing cursor
theme shows up in CI instead of only in the session log.
