#!/usr/bin/env bash
# Install the Zaldros visual layer into a root filesystem and make it the default for every user.
# Run inside the image chroot during the build, or with sudo on a running system.
#
#   install-visual-theme.sh [--dest ROOTFS] [--cursors DIR] [--assets DIR] [--variant dark|light]
#
# What is ours and what is borrowed (ADR-0010, 2026-08-26):
#   ours     — icon theme (built here from assets/icons), colour scheme, GTK overrides, KWin config
#   borrowed — the cursor theme only: Fluent-icon-theme/cursors (GPL-3.0), copied unmodified
# Licences and obligations: docs/VISUAL_LICENSE_AUDIT.md
set -euo pipefail

DEST="/"
CURSOR_SRC="${CURSOR_SRC:-/usr/src/Fluent-icon-theme}"
ASSETS="${ASSETS:-/opt/zaldros/assets}"
VARIANT="dark"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dest)    DEST="$2"; shift 2 ;;
    --cursors) CURSOR_SRC="$2"; shift 2 ;;
    --assets)  ASSETS="$2"; shift 2 ;;
    --variant) VARIANT="$2"; shift 2 ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

[[ -d "$CURSOR_SRC/cursors/dist-dark/cursors" ]] || { echo "no prebuilt cursors in $CURSOR_SRC" >&2; exit 1; }
[[ -d "$ASSETS/icons/apps" ]] || { echo "no icon assets in $ASSETS" >&2; exit 1; }

THEMES="$DEST/usr/share/themes"
ICONS="$DEST/usr/share/icons"
mkdir -p "$THEMES" "$ICONS"

CURSOR_THEME="Fluent-dark-cursors"
[[ "$VARIANT" == "light" ]] && CURSOR_THEME="Fluent-cursors"

# ---------------------------------------------------------------- cursors (the only borrowed pack)
# Copied verbatim, names kept: a GPL-3 work stays identifiable, and the licence travels with it.
rm -rf "$ICONS/Fluent-cursors" "$ICONS/Fluent-dark-cursors"
cp -r "$CURSOR_SRC/cursors/dist"      "$ICONS/Fluent-cursors"
cp -r "$CURSOR_SRC/cursors/dist-dark" "$ICONS/Fluent-dark-cursors"
install -Dm644 "$CURSOR_SRC/cursors/LICENSE" "$DEST/usr/share/doc/zaldros/licenses/Fluent-icon-theme-COPYING"

# Xcursor only looks at the "default" theme unless an application asks otherwise, so the choice has
# to exist as a theme of that name; without this the session logs "no cursor theme" and falls back
# to the X11 core font cursor.
install -Dm644 /dev/stdin "$ICONS/default/index.theme" <<EOF
[Icon Theme]
Name=Default
Comment=Zaldros default pointer
Inherits=$CURSOR_THEME
EOF

# ------------------------------------------------------------------- our own icon theme (Zaldros)
# Built from the icons in this repository, not from a theme pack. Freedesktop layout so every
# toolkit (Qt, GTK, the shell's QIcon.fromTheme) resolves the same names.
# ------------------------------------------------------------------- borrowed icon fallback pack
# Our own set is 116 hand-picked SVGs; Dolphin, Konsole and every KDE dialog ask for thousands of
# names we do not have and fall back to hicolor, which is mostly empty. The Windows-Eleven icon
# theme (store.kde.org/p/1977340, GPL-3, zayronXIO) covers ~29 700 names in the Windows 11 style,
# so it becomes the *parent* of ours: our icons win, its icons fill the gaps.
FALLBACK_ICONS="Windows-eleven"
ICON_PACK="$ASSETS/themes/icons/Windows-Eleven-icons-4.8.8.tar.xz"
if [[ -f "$ICON_PACK" ]]; then
  rm -rf "$ICONS/Windows-Eleven"
  tar xf "$ICON_PACK" -C "$ICONS"
  install -Dm644 "$ASSETS/themes/NOTICE.md" "$DEST/usr/share/doc/zaldros/licenses/theme-assets-NOTICE.md"
else
  echo "warning: no icon fallback pack at $ICON_PACK, Zaldros icons will stand alone" >&2
  FALLBACK_ICONS="hicolor"
fi

ZICONS="$ICONS/Zaldros"
rm -rf "$ZICONS"
install -d "$ZICONS/apps/scalable" "$ZICONS/places/scalable" "$ZICONS/actions/scalable"
cp "$ASSETS/icons/apps/"*.svg   "$ZICONS/apps/scalable/"
cp "$ASSETS/icons/places/"*.svg "$ZICONS/places/scalable/"
cp "$ASSETS/icons/fluent/"*.svg "$ZICONS/actions/scalable/"
install -Dm644 /dev/stdin "$ZICONS/index.theme" <<EOF
[Icon Theme]
Name=Zaldros
Comment=Zaldros system icons
Inherits=$FALLBACK_ICONS,hicolor
Directories=apps/scalable,places/scalable,actions/scalable

[apps/scalable]
Context=Applications
Size=48
MinSize=16
MaxSize=512
Type=Scalable

[places/scalable]
Context=Places
Size=48
MinSize=16
MaxSize=512
Type=Scalable

[actions/scalable]
Context=Actions
Size=24
MinSize=16
MaxSize=512
Type=Scalable
EOF
if command -v gtk-update-icon-cache >/dev/null; then
  gtk-update-icon-cache --force --quiet "$ZICONS" || true
fi
# The app and place SVGs are still GPL-3 work from upstream icon themes, so their COPYING and
# AUTHORS travel with the image even though the theme itself is assembled here.
for directory in apps places fluent; do
  for notice in COPYING AUTHORS LICENSE; do
    [[ -f "$ASSETS/icons/$directory/$notice" ]] &&
      install -Dm644 "$ASSETS/icons/$directory/$notice" \
        "$DEST/usr/share/doc/zaldros/licenses/icons-$directory-$notice"
  done
done

icon_theme="Zaldros"
scheme="prefer-dark"; [[ "$VARIANT" == "light" ]] && scheme="prefer-light"

install -d "$DEST/etc/xdg" "$DEST/etc/skel/.config/gtk-3.0" "$DEST/etc/skel/.config/gtk-4.0"

# ------------------------------------------------------------------------ Qt widget style (Kvantum)
# Our shell is QtQuick and draws itself, but Dolphin and Konsole are QWidget applications: they take
# their buttons, tabs, scrollbars and menus from the Qt style. Breeze made every one of them look
# like KDE. Kvantum is an SVG-driven style engine that needs no Plasma session, and the
# "Windows-modern" theme (GPL-3, Jeysef/KDE-Windows-Modern, itself built on Fluent-kde and
# Win11OS-kde) is the Windows 11 skin for it. Package: qt6-style-kvantum (1.1.5-1 in resolute).
KVANTUM_STYLE="kvantum-dark"
[[ "$VARIANT" == "light" ]] && KVANTUM_STYLE="kvantum"
KVANTUM_SRC="$ASSETS/themes/kvantum/Windows-modern"
if [[ -d "$KVANTUM_SRC" ]]; then
  rm -rf "$DEST/usr/share/Kvantum/Windows-modern"
  install -d "$DEST/usr/share/Kvantum"
  cp -r "$KVANTUM_SRC" "$DEST/usr/share/Kvantum/"
  install -Dm644 "$ASSETS/themes/kvantum/LICENSE" \
    "$DEST/usr/share/doc/zaldros/licenses/Windows-modern-Kvantum-COPYING"
  install -Dm644 "$ASSETS/themes/kvantum/ATTRIBUTION.md" \
    "$DEST/usr/share/doc/zaldros/licenses/Windows-modern-Kvantum-ATTRIBUTION.md"
  # Kvantum reads Kvantum/kvantum.kvconfig (capital K) from XDG config dirs; the live user has no
  # home yet, so the default must exist system-wide *and* in the skeleton.
  for target in "$DEST/etc/xdg/Kvantum/kvantum.kvconfig" \
                "$DEST/etc/skel/.config/Kvantum/kvantum.kvconfig"; do
    install -Dm644 /dev/stdin "$target" <<EOF
[General]
theme=Windows-modern
EOF
  done
  widget_style="$KVANTUM_STYLE"
else
  echo "warning: no Kvantum theme in $KVANTUM_SRC, KDE applications stay on Breeze" >&2
  widget_style="Breeze"
fi

# ------------------------------------------------------------------------------- KDE colour scheme
# Run #29, from the live boot log: `Could not find color scheme "ZaldrosDark" falling back to
# BreezeLight`. kdeglobals named a scheme that was never installed, so every KDE application in the
# image — Dolphin, Konsole, the KWin decoration — ran in Breeze *light* on a dark desktop.
# The values are the same tokens as qml/ZaldrosTheme/Theme.qml; KDE wants decimal r,g,b.
if [[ "$VARIANT" == "light" ]]; then
  c_window="243,243,243"; c_text="27,27,27"; c_view="255,255,255"; c_button="251,251,251"
  c_accent="0,103,192";   c_accent_text="255,255,255"; c_scheme_name="ZaldrosLight"
else
  c_window="32,32,32";    c_text="255,255,255"; c_view="25,25,25";  c_button="44,44,44"
  c_accent="96,205,255";  c_accent_text="0,36,61";     c_scheme_name="ZaldrosDark"
fi
install -Dm644 /dev/stdin "$DEST/usr/share/color-schemes/$c_scheme_name.colors" <<EOF
[General]
ColorScheme=$c_scheme_name
Name=$c_scheme_name
shadeSortColumn=true

[Colors:Window]
BackgroundNormal=$c_window
BackgroundAlternate=$c_button
ForegroundNormal=$c_text
ForegroundInactive=122,122,122
DecorationFocus=$c_accent
DecorationHover=$c_accent

[Colors:View]
BackgroundNormal=$c_view
BackgroundAlternate=$c_window
ForegroundNormal=$c_text
ForegroundInactive=122,122,122
DecorationFocus=$c_accent
DecorationHover=$c_accent

[Colors:Button]
BackgroundNormal=$c_button
BackgroundAlternate=$c_window
ForegroundNormal=$c_text
DecorationFocus=$c_accent
DecorationHover=$c_accent

[Colors:Selection]
BackgroundNormal=$c_accent
BackgroundAlternate=$c_accent
ForegroundNormal=$c_accent_text
DecorationFocus=$c_accent
DecorationHover=$c_accent

[Colors:Tooltip]
BackgroundNormal=$c_button
ForegroundNormal=$c_text

[Colors:Complementary]
BackgroundNormal=$c_window
ForegroundNormal=$c_text

[WM]
activeBackground=$c_window
activeForeground=$c_text
inactiveBackground=$c_window
inactiveForeground=122,122,122
EOF

# --------------------------------------------------------------------- window decoration (Aurorae)
# Aurorae is KWin's SVG decoration engine and ships in `kwin-style-aurorae` — it does *not* need
# plasmashell, which is why this is the one part of the "windows-eleven" Plasma global themes that
# fits our architecture. Breeze drew KDE-style title bars on every non-shell window (Dolphin,
# Konsole); these draw Windows 11 ones with the caption buttons on the right.
AURORAE_THEME="Windows-Eleven-Dark"
[[ "$VARIANT" == "light" ]] && AURORAE_THEME="Windows-Eleven"
AURORAE_SRC="$ASSETS/themes/aurorae"
if [[ -d "$AURORAE_SRC/$AURORAE_THEME" ]]; then
  install -d "$DEST/usr/share/aurorae/themes"
  rm -rf "$DEST/usr/share/aurorae/themes/Windows-Eleven" \
         "$DEST/usr/share/aurorae/themes/Windows-Eleven-Dark"
  cp -r "$AURORAE_SRC/Windows-Eleven" "$AURORAE_SRC/Windows-Eleven-Dark" \
        "$DEST/usr/share/aurorae/themes/"
  decoration_library="org.kde.kwin.aurorae"
  decoration_theme="__aurorae__svg__$AURORAE_THEME"
else
  echo "warning: no Aurorae theme in $AURORAE_SRC, falling back to Breeze decorations" >&2
  decoration_library="org.kde.breeze"
  decoration_theme=""
fi

# ------------------------------------------------------------------------------------- UI font
# The interface is Russian, so the UI font has to *have* Cyrillic. Selawik did not (Latin-only
# cmap), the shell silently fell back to DejaVu Sans and every label looked like plain Linux.
# PT Sans (SIL OFL 1.1, ParaType) is the closest shipped match to Segoe UI Cyrillic measured
# against assets/refs — see tools/visual/font_match.py. It is installed system-wide so KWin,
# Dolphin and Konsole use it too, not only our shell.
UI_FONT_FAMILY="PT Sans"
FONT_SRC="$ASSETS/fonts/pt-sans"
[[ -d "$FONT_SRC" ]] || { echo "no UI font in $FONT_SRC" >&2; exit 1; }
install -d "$DEST/usr/share/fonts/truetype/zaldros"
install -m644 "$FONT_SRC"/*.ttf "$DEST/usr/share/fonts/truetype/zaldros/"
install -Dm644 "$FONT_SRC/LICENSE.txt" "$DEST/usr/share/doc/zaldros/licenses/PT-Sans-OFL.txt"

# Anything that asks fontconfig for a generic sans — or for Segoe UI by name — gets our font.
install -Dm644 /dev/stdin "$DEST/etc/fonts/conf.d/60-zaldros-ui-font.conf" <<EOF
<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
  <alias><family>sans-serif</family><prefer><family>$UI_FONT_FAMILY</family></prefer></alias>
  <alias><family>system-ui</family><prefer><family>$UI_FONT_FAMILY</family></prefer></alias>
  <alias binding="same"><family>Segoe UI</family><accept><family>$UI_FONT_FAMILY</family></accept></alias>
  <alias binding="same"><family>Selawik</family><accept><family>$UI_FONT_FAMILY</family></accept></alias>
</fontconfig>
EOF
command -v fc-cache >/dev/null && fc-cache -f "$DEST/usr/share/fonts/truetype/zaldros" >/dev/null || true

# ---------------------------------------------------------------------------- Qt / KDE defaults
cat > "$DEST/etc/xdg/kdeglobals" <<EOF
[Icons]
Theme=$icon_theme

[KDE]
LookAndFeelPackage=org.zaldros.desktop
widgetStyle=$widget_style

[General]
ColorScheme=$c_scheme_name
font=$UI_FONT_FAMILY,10,-1,5,50,0,0,0,0,0
menuFont=$UI_FONT_FAMILY,10,-1,5,50,0,0,0,0,0
smallestReadableFont=$UI_FONT_FAMILY,8,-1,5,50,0,0,0,0,0
toolBarFont=$UI_FONT_FAMILY,10,-1,5,50,0,0,0,0,0

[WM]
activeFont=$UI_FONT_FAMILY,10,-1,5,50,0,0,0,0,0
EOF

# KDE reads the pointer from kcminputrc, not from kdeglobals.
cat > "$DEST/etc/xdg/kcminputrc" <<EOF
[Mouse]
cursorTheme=$CURSOR_THEME
cursorSize=24
EOF

# The X11/Wayland fallback path for everything that predates the settings daemons.
install -Dm644 /dev/stdin "$DEST/etc/X11/Xresources/x11-common" <<EOF
Xcursor.theme: $CURSOR_THEME
Xcursor.size: 24
EOF
install -Dm644 /dev/stdin "$DEST/etc/profile.d/zaldros-cursor.sh" <<EOF
export XCURSOR_THEME=$CURSOR_THEME
export XCURSOR_SIZE=24
EOF

# ------------------------------------------------------------------------------- GTK applications
# No third-party GTK theme. GTK apps run on the stock Adwaita with our tokens applied on top, so a
# GTK window is close to the shell's palette without pulling in a pack we would then have to patch.
# GTK parity beyond colour is tracked in docs/VISUAL_COMPONENT_MATRIX.md, it is not claimed here.
if [[ "$VARIANT" == "dark" ]]; then
  gtk_bg="#202020"; gtk_fg="#ffffff"; gtk_base="#191919"; gtk_accent="#60cdff"; gtk_accent_fg="#00243d"
  prefer_dark=1
else
  gtk_bg="#f3f3f3"; gtk_fg="#1b1b1b"; gtk_base="#ffffff"; gtk_accent="#0067c0"; gtk_accent_fg="#ffffff"
  prefer_dark=0
fi
for version in 3.0 4.0; do
  cat > "$DEST/etc/skel/.config/gtk-$version/settings.ini" <<EOF
[Settings]
gtk-theme-name=Adwaita
gtk-icon-theme-name=$icon_theme
gtk-font-name=$UI_FONT_FAMILY 10
gtk-application-prefer-dark-theme=$prefer_dark
gtk-cursor-theme-name=$CURSOR_THEME
gtk-cursor-theme-size=24
gtk-decoration-layout=:minimize,maximize,close
EOF
  cat > "$DEST/etc/skel/.config/gtk-$version/gtk.css" <<EOF
/* Zaldros tokens on top of Adwaita — same values as qml/ZaldrosTheme/Theme.qml */
@define-color accent_color $gtk_accent;
@define-color accent_bg_color $gtk_accent;
@define-color accent_fg_color $gtk_accent_fg;
@define-color theme_bg_color $gtk_bg;
@define-color theme_fg_color $gtk_fg;
@define-color theme_base_color $gtk_base;
@define-color window_bg_color $gtk_bg;
@define-color window_fg_color $gtk_fg;
@define-color view_bg_color $gtk_base;
window { border-radius: 8px; }
EOF
done

# System-wide defaults for GNOME-schema-aware applications (also read by portals)
install -d "$DEST/usr/share/glib-2.0/schemas"
cat > "$DEST/usr/share/glib-2.0/schemas/90_zaldros-theme.gschema.override" <<EOF
[org.gnome.desktop.interface]
gtk-theme='Adwaita'
icon-theme='$icon_theme'
cursor-theme='$CURSOR_THEME'
cursor-size=24
font-name='$UI_FONT_FAMILY 10'
color-scheme='$scheme'
EOF
if command -v glib-compile-schemas >/dev/null; then
  glib-compile-schemas "$DEST/usr/share/glib-2.0/schemas" >/dev/null
fi

# ------------------------------------------------------------------------------------------ KWin
# Windows 11 geometry: rounded corners, blur behind panels and menus, no titlebar on maximised
# windows. Decorations are Breeze with no border until our own Aurorae theme exists — an honest
# placeholder, not a claim of parity (VISUAL_COMPONENT_MATRIX.md).
install -Dm644 /dev/stdin "$DEST/etc/xdg/kwinrc" <<EOF
[Compositing]
Enabled=true
Backend=OpenGL
WindowsBlockCompositing=false

[Plugins]
roundedcornersEnabled=true
blurEnabled=true
contrastEnabled=true
kwin4_effect_squashEnabled=true

[Effect-blur]
BlurStrength=8
NoiseStrength=2

[Windows]
# Run #28: the maintainer wants rounded corners on every window, so a maximised window keeps its
# decoration and its corners instead of going borderless and square.
BorderlessMaximizedWindows=false

# KWin 6 loads kdecoration3 plugins but still reads this group name (kwin/src/decorations).
[org.kde.kdecoration2]
library=$decoration_library
theme=$decoration_theme
BorderSize=None
ButtonsOnLeft=
ButtonsOnRight=IAX

# Alt+Tab. Windows 11 shows large window thumbnails in a grid, so thumbnail_grid is the closest
# switcher KWin ships; the alternative list layout is left on the same value so both key paths
# look the same instead of one of them falling back to the KDE default.
[TabBox]
LayoutName=thumbnail_grid
ShowTabBox=true
HighlightWindows=true
SwitchingMode=0
MultiScreenMode=0
ApplicationsMode=0
MinimizedMode=0

[TabBoxAlternative]
LayoutName=thumbnail_grid
EOF

# The switcher only appears if some process holds the Alt+Tab grab. KWin asks the global
# accelerator daemon for it at startup and the daemon reads its defaults from here, so this file
# is what actually makes Alt+Tab live in a session with no Plasma behind it (run #27).
install -Dm644 /dev/stdin "$DEST/etc/xdg/kglobalshortcutsrc" <<'EOF'
[kwin]
_k_friendly_name=KWin
Walk Through Windows=Alt+Tab,Alt+Tab,Walk Through Windows
Walk Through Windows (Reverse)=Alt+Shift+Backtab,Alt+Shift+Backtab,Walk Through Windows (Reverse)
Walk Through Windows of Current Application=Alt+`,Alt+`,Walk Through Windows of Current Application
Show Desktop=Meta+D,Meta+D,Peek at Desktop
Window Close=Alt+F4,Alt+F4,Close Window
Window Maximize=Meta+Up,Meta+Up,Maximize Window
Window Minimize=Meta+Down,Meta+Down,Minimize Window
Window Quick Tile Left=Meta+Left,Meta+Left,Quick Tile Window to the Left
Window Quick Tile Right=Meta+Right,Meta+Right,Quick Tile Window to the Right
EOF

# The shell reads this file: it must never disagree with what was installed above.
install -Dm644 /dev/stdin "$DEST/etc/zaldros/visual.conf" <<EOF
icon_theme=$icon_theme
icon_fallback=$FALLBACK_ICONS
widget_style=$widget_style
decoration=$decoration_library
decoration_theme=$decoration_theme
gtk_theme=Adwaita
cursor_theme=$CURSOR_THEME
font=$UI_FONT_FAMILY
taskbar_position=bottom
taskbar_alignment=center
corner_radius=10
EOF

echo "installed: icon theme $icon_theme (ours) + cursor theme $CURSOR_THEME (Fluent, GPL-3) into $DEST"
