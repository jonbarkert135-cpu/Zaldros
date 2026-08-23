#!/usr/bin/env bash
# Fetch the upstream visual sources that install-visual-theme.sh consumes.
# Pinned to commits so an image build is reproducible (spec PART 1 §12).
set -euo pipefail

DEST="${1:-/usr/src}"
clone() {  # url dir ref
  local url="$1" dir="$DEST/$2" ref="$3"
  [[ -d "$dir/.git" ]] || git clone --quiet "$url" "$dir"
  git -C "$dir" fetch --quiet origin "$ref" || true
  git -C "$dir" checkout --quiet "$ref"
  echo "$2 @ $(git -C "$dir" rev-parse --short HEAD)"
}

mkdir -p "$DEST"
clone https://github.com/yeyushengfan258/Win11-gtk-theme.git  Win11-gtk-theme  "${GTK_REF:-main}"
clone https://github.com/yeyushengfan258/Win11-icon-theme.git Win11-icon-theme "${ICON_REF:-main}"
clone https://github.com/vinceliuice/Fluent-icon-theme.git    Fluent-icon-theme "${CURSOR_REF:-master}"

# Cursors come from Fluent-icon-theme; its installer lives in the cursors/ subdirectory.
echo "next: install-visual-theme.sh --dest <rootfs> --gtk $DEST/Win11-gtk-theme --icons $DEST/Win11-icon-theme"
