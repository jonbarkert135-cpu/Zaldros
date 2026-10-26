#!/usr/bin/env bash
# Fetch the one upstream visual source Zaldros still ships: the cursor theme.
#
# ADR-0010 (2026-08-26): cursors are the only third-party *theme* we install. GTK and icon theme
# packs are no longer fetched — the look is drawn by our own shell and our own icon set, because a
# theme pack cannot reach Windows 11 pixel parity and hides where a mismatch comes from.
# Pinned to a commit so an image build is reproducible (spec PART 1 §12).
set -euo pipefail

DEST="${1:-/usr/src}"
CURSOR_REF="${CURSOR_REF:-c8a244f571ef8fb47812bdc9dbce76546cedce69}"
[[ "$CURSOR_REF" =~ ^[0-9a-f]{40}$ ]] || { echo "CURSOR_REF must be a full commit SHA" >&2; exit 1; }

mkdir -p "$DEST"
dir="$DEST/Fluent-icon-theme"
[[ -d "$dir/.git" ]] || git clone --quiet --filter=blob:none --no-checkout \
  https://github.com/vinceliuice/Fluent-icon-theme.git "$dir"
git -C "$dir" sparse-checkout set --no-cone cursors >/dev/null
git -C "$dir" fetch --quiet origin "$CURSOR_REF"
git -C "$dir" checkout --quiet --detach "$CURSOR_REF"
[[ "$(git -C "$dir" rev-parse HEAD)" == "$CURSOR_REF" ]] || exit 1
echo "Fluent-icon-theme @ $(git -C "$dir" rev-parse HEAD) (cursors/ only)"

# The cursors are prebuilt in cursors/dist and cursors/dist-dark, so no inkscape/xcursorgen at
# build time. install-visual-theme.sh copies them unmodified.
echo "next: install-visual-theme.sh --dest <rootfs> --cursors $dir"
