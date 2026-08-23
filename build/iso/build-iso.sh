#!/usr/bin/env bash
# Build a bootable Zaldros live ISO for one architecture variant.
# Needs root and: debootstrap squashfs-tools xorriso grub-efi-amd64-bin grub-pc-bin mtools dosfstools
# Usage: sudo ./build-iso.sh <variant> <out.iso>   variant = full | services | legacy
set -euo pipefail

VARIANT="${1:?variant: full|services|legacy}"
OUT="${2:-zaldros-$VARIANT.iso}"
SUITE="${SUITE:-resolute}"          # Ubuntu 26.04 LTS — first Ubuntu LTS with Plasma 6 / KWin 6
MIRROR="${MIRROR:-http://archive.ubuntu.com/ubuntu}"
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
WORK="${WORK:-$(mktemp -d)}"
ROOT="$WORK/rootfs"

# Package set per variant — the three architectures we are comparing.
BASE="ubuntu-minimal linux-image-generic systemd-sysv casper network-manager pipewire pipewire-pulse wireplumber sddm dolphin konsole fonts-dejavu-core python3 python3-pyside6.qtquick"
case "$VARIANT" in
  full)     EXTRA="plasma-desktop plasma-workspace kwin-wayland" ;;
  services) EXTRA="kwin-wayland plasma-nm plasma-pa powerdevil kscreen" ;;
  legacy)   EXTRA="kwin-wayland layer-shell-qt qml6-module-qtquick-controls" ;;
  *) echo "unknown variant $VARIANT" >&2; exit 2 ;;
esac

# Ubuntu publishes an official minimal rootfs tarball for the release, so we unpack that instead of
# re-deriving it with debootstrap: no dependency on the runner's debootstrap version knowing the
# suite, and it is faster. debootstrap stays as the fallback if the tarball is unavailable.
BASE_TARBALL="${BASE_TARBALL:-https://cdimage.ubuntu.com/ubuntu-base/releases/$SUITE/release/ubuntu-base-26.04-base-amd64.tar.gz}"
mkdir -p "$ROOT"
echo "== fetch base rootfs: $BASE_TARBALL"
if curl -fsSL "$BASE_TARBALL" | tar -xz -C "$ROOT"; then
  echo "== unpacked the official Ubuntu base rootfs"
else
  echo "== tarball unavailable, falling back to debootstrap $SUITE"
  # Older debootstrap has no script for a newer suite; Ubuntu suites share the gutsy-derived script.
  [ -e "/usr/share/debootstrap/scripts/$SUITE" ] || ln -s gutsy "/usr/share/debootstrap/scripts/$SUITE"
  debootstrap --arch=amd64 --variant=minbase --components=main,universe "$SUITE" "$ROOT" "$MIRROR" \
    || { echo "== debootstrap failed, tail of its log:"; tail -50 "$ROOT/debootstrap/debootstrap.log" 2>/dev/null; exit 1; }
fi
cp /etc/resolv.conf "$ROOT/etc/resolv.conf"
rm -f "$ROOT/etc/apt/sources.list"   # the base image ships deb822 sources; ours replaces them

cat > "$ROOT/etc/apt/sources.list.d/ubuntu.sources" <<EOF
Types: deb
URIs: $MIRROR
Suites: $SUITE $SUITE-updates
Components: main universe restricted multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
EOF

mount --bind /dev "$ROOT/dev"; mount -t proc proc "$ROOT/proc"; mount -t sysfs sys "$ROOT/sys"
trap 'umount -l "$ROOT/dev" "$ROOT/proc" "$ROOT/sys" 2>/dev/null || true' EXIT

echo "== install packages ($VARIANT)"
chroot "$ROOT" env DEBIAN_FRONTEND=noninteractive sh -c \
  "apt-get update -qq && apt-get install -y --no-install-recommends $BASE $EXTRA"

echo "== install the Zaldros shell, theme scripts and self-test"
mkdir -p "$ROOT/opt/zaldros"
cp -a "$REPO/shell/zaldros-shell/zaldros_shell" "$REPO/shell/zaldros-shell/qml" "$ROOT/opt/zaldros/"
cp -a "$REPO/assets" "$ROOT/opt/zaldros/assets"
cp -a "$REPO/system/theme" "$ROOT/opt/zaldros/theme"
cp "$(dirname "$0")/selftest.py" "$ROOT/usr/local/bin/zaldros-selftest"
cp "$(dirname "$0")/uitest.py"   "$ROOT/usr/local/bin/zaldros-uitest"
chmod +x "$ROOT/usr/local/bin/zaldros-selftest" "$ROOT/usr/local/bin/zaldros-uitest"
echo "$VARIANT" > "$ROOT/etc/zaldros-variant"

# The themes: run the real upstream installers inside the image (no network at boot time).
chroot "$ROOT" sh -c "apt-get install -y --no-install-recommends git sassc && /opt/zaldros/theme/fetch-sources.sh /usr/src && /opt/zaldros/theme/install-visual-theme.sh --dest / --variant dark"

# Autologin straight into the variant's session, so a boot test needs no keyboard.
install -d "$ROOT/etc/sddm.conf.d"
printf '[Autologin]\nUser=zaldros\nSession=zaldros.desktop\n' > "$ROOT/etc/sddm.conf.d/10-autologin.conf"
chroot "$ROOT" useradd -m -s /bin/bash zaldros
chroot "$ROOT" sh -c 'passwd -d zaldros'

case "$VARIANT" in
  full)     SESSION_EXEC="startplasma-wayland" ;;
  services) SESSION_EXEC="/usr/local/bin/zaldros-session" ;;
  legacy)   SESSION_EXEC="/usr/local/bin/zaldros-session" ;;
esac
cat > "$ROOT/usr/local/bin/zaldros-session" <<'EOS'
#!/bin/sh
# KWin as the compositor, the Zaldros shell as the only shell process. No plasmashell.
export QT_QPA_PLATFORM=wayland PYTHONPATH=/opt/zaldros
exec kwin_wayland --xwayland -- python3 -m zaldros_shell
EOS
chmod +x "$ROOT/usr/local/bin/zaldros-session"
install -d "$ROOT/usr/share/wayland-sessions"
printf '[Desktop Entry]\nName=Zaldros\nExec=%s\nType=Application\n' "$SESSION_EXEC" \
  > "$ROOT/usr/share/wayland-sessions/zaldros.desktop"

# Self-test unit: runs only when the kernel cmdline asks for it, then powers the VM off.
cat > "$ROOT/etc/systemd/system/zaldros-selftest.service" <<'EOS'
[Unit]
Description=Zaldros boot self-test
After=graphical.target
ConditionKernelCommandLine=zaldros.selftest
[Service]
Type=oneshot
ExecStart=/usr/local/bin/zaldros-selftest --serial /dev/ttyS0
# Stage 2: pause so the host can inject input over QMP, then run the UI interaction test.
ExecStart=/bin/sleep 45
ExecStart=/bin/sh -c '/usr/local/bin/zaldros-uitest > /dev/ttyS0 2>/var/log/zaldros-uitest.err'
TimeoutStartSec=600
ExecStopPost=/usr/bin/systemctl poweroff
[Install]
WantedBy=graphical.target
EOS
chroot "$ROOT" systemctl enable zaldros-selftest.service

echo "== squashfs + ISO"
umount -l "$ROOT/dev" "$ROOT/proc" "$ROOT/sys" 2>/dev/null || true; trap - EXIT
install -d "$WORK/iso/casper" "$WORK/iso/boot/grub"
mksquashfs "$ROOT" "$WORK/iso/casper/filesystem.squashfs" -comp zstd -Xcompression-level 15 -noappend
cp "$ROOT"/boot/vmlinuz-* "$WORK/iso/casper/vmlinuz"
cp "$ROOT"/boot/initrd.img-* "$WORK/iso/casper/initrd"
cat > "$WORK/iso/boot/grub/grub.cfg" <<EOS
set timeout=1
menuentry "Zaldros OS ($VARIANT)" {
  linux /casper/vmlinuz boot=casper quiet console=ttyS0,115200 zaldros.selftest
  initrd /casper/initrd
}
EOS
grub-mkrescue -o "$OUT" "$WORK/iso" -- -volid ZALDROS
echo "ISO: $OUT ($(du -h "$OUT" | cut -f1))"
