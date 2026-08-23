#!/usr/bin/env bash
# Install the Windows-11-like visual layer into a Zaldros root filesystem and make it the default
# for every user. Run inside the image chroot during the build, or with sudo on a running system.
#
#   install-visual-theme.sh [--dest ROOTFS] [--gtk DIR] [--icons DIR] [--variant dark|light]
#
# Sources are the upstream projects, used unmodified through their own installers:
#   Win11-gtk-theme   (GPL-3.0)  -> /usr/share/themes/Win11-*
#   Win11-icon-theme  (GPL-3.0)  -> /usr/share/icons/Win11
# Licences and obligations: docs/VISUAL_LICENSE_AUDIT.md
set -euo pipefail

DEST="/"
GTK_SRC="${GTK_SRC:-/usr/src/Win11-gtk-theme}"
ICON_SRC="${ICON_SRC:-/usr/src/Win11-icon-theme}"
VARIANT="dark"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dest)    DEST="$2"; shift 2 ;;
    --gtk)     GTK_SRC="$2"; shift 2 ;;
    --icons)   ICON_SRC="$2"; shift 2 ;;
    --variant) VARIANT="$2"; shift 2 ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

for dir in "$GTK_SRC" "$ICON_SRC"; do
  [[ -x "$dir/install.sh" ]] || { echo "no install.sh in $dir" >&2; exit 1; }
done

THEMES="$DEST/usr/share/themes"
ICONS="$DEST/usr/share/icons"
mkdir -p "$THEMES" "$ICONS"

# Upstream installers do the actual work — we do not re-implement or patch them.
# GTK: round windows, blurred panels, default title buttons; both colour schemes are installed so
# the user can switch light/dark without a second install.
# Flags verified against the upstream usage text: -d/--dest, -t/--theme, -c/--color, -s/--size,
# -i/--icon and --tweaks (round = rounded windows, blur = blurred panels).
"$GTK_SRC/install.sh" --dest "$THEMES" --theme default --color dark --color light \
                      --size standard --icon default --tweaks round blur
"$ICON_SRC/install.sh" --dest "$ICONS" --name Win11 --theme default

gtk_theme="Win11-Dark"; icon_theme="Win11-dark"; scheme="prefer-dark"
if [[ "$VARIANT" == "light" ]]; then
  gtk_theme="Win11-Light"; icon_theme="Win11"; scheme="prefer-light"
fi

install -d "$DEST/etc/xdg" "$DEST/etc/skel/.config/gtk-3.0" "$DEST/etc/skel/.config/gtk-4.0"

# Qt / KDE applications (Dolphin, Konsole, Ark, Spectacle and the Zaldros shell read the icon theme)
cat > "$DEST/etc/xdg/kdeglobals" <<EOF
[Icons]
Theme=$icon_theme

[KDE]
LookAndFeelPackage=org.zaldros.desktop
widgetStyle=Breeze

[General]
ColorScheme=ZaldrosDark
EOF

# GTK 3 and GTK 4 applications
for version in 3.0 4.0; do
  cat > "$DEST/etc/skel/.config/gtk-$version/settings.ini" <<EOF
[Settings]
gtk-theme-name=$gtk_theme
gtk-icon-theme-name=$icon_theme
gtk-font-name=Selawik 10
gtk-application-prefer-dark-theme=$([[ "$VARIANT" == dark ]] && echo 1 || echo 0)
gtk-cursor-theme-name=Win11-cursors
EOF
done

# System-wide defaults for GNOME-schema-aware applications (also read by portals)
install -d "$DEST/usr/share/glib-2.0/schemas"
cat > "$DEST/usr/share/glib-2.0/schemas/90_zaldros-theme.gschema.override" <<EOF
[org.gnome.desktop.interface]
gtk-theme='$gtk_theme'
icon-theme='$icon_theme'
font-name='Selawik 10'
color-scheme='$scheme'
EOF
if command -v glib-compile-schemas >/dev/null; then
  glib-compile-schemas "$DEST/usr/share/glib-2.0/schemas" >/dev/null
fi

# KWin: Windows 11 geometry — rounded corners, blur behind panels and menus, no titlebar on
# maximised windows. Values live in a config file, not in shell code.
install -Dm644 /dev/stdin "$DEST/etc/xdg/kwinrc" <<'EOF'
[Compositing]
Enabled=true
Backend=OpenGL
WindowsBlockCompositing=false

[Plugins]
blurEnabled=true
contrastEnabled=true
kwin4_effect_squashEnabled=true

[Effect-blur]
BlurStrength=8
NoiseStrength=2

[Windows]
BorderlessMaximizedWindows=true

[org.kde.kdecoration2]
library=org.kde.kwin.aurorae
theme=__aurorae__svg__Win11
BorderSize=None
ButtonsOnLeft=
ButtonsOnRight=IAX
EOF

# The Zaldros shell reads this to pick the icon theme instead of its vendored fallback set.
install -Dm644 /dev/stdin "$DEST/etc/zaldros/visual.conf" <<EOF
icon_theme=$icon_theme
gtk_theme=$gtk_theme
cursor_theme=Win11-cursors
font=Selawik
taskbar_position=bottom
taskbar_alignment=center
corner_radius=10
EOF

echo "installed: $gtk_theme + $icon_theme into $DEST"
