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

# --- diagnostics -------------------------------------------------------------------------------
# Every run leaves a debug directory behind, whether it succeeds or fails, so a failure is read from
# evidence instead of guessed at. DEBUG_DIR is uploaded as its own artifact per variant.
DEBUG_DIR="${DEBUG_DIR:-$PWD/build-debug-$VARIANT}"
mkdir -p "$DEBUG_DIR"
: > "$DEBUG_DIR/steps.tsv"

step() {                              # step <name> <command...> — records the exit code of each step
  local name="$1"; shift
  echo "== $name"
  local rc=0
  "$@" > >(tee -a "$DEBUG_DIR/$name.log") 2> >(tee -a "$DEBUG_DIR/$name.log" >&2) || rc=$?
  printf '%s\t%s\t%s\n' "$name" "$rc" "$*" >> "$DEBUG_DIR/steps.tsv"
  [ "$rc" -eq 0 ] || echo "!! step '$name' failed with exit code $rc: $*"
  return "$rc"
}

collect_debug() {                     # runs on every exit, including failures
  local rc=$?
  {
    echo "=== exit code: $rc"; echo "=== date: $(date -Is)"
    echo "=== uname -a"; uname -a
    echo "=== host /etc/os-release"; cat /etc/os-release
    echo "=== df -h"; df -h
    echo "=== free -h"; free -h
    echo "=== mount"; mount
    echo "=== dpkg --print-architecture (host)"; dpkg --print-architecture
    echo "=== rootfs: $ROOT"; ls -la "$ROOT" 2>/dev/null | head -40
    echo "=== rootfs size"; du -sh "$ROOT" 2>/dev/null
    echo "=== rootfs /etc/os-release"; cat "$ROOT/etc/os-release" 2>/dev/null
    echo "=== rootfs dpkg --print-architecture"; chroot "$ROOT" dpkg --print-architecture 2>&1
    echo "=== rootfs /etc/resolv.conf"; cat "$ROOT/etc/resolv.conf" 2>/dev/null
    echo "=== rootfs DNS check"; chroot "$ROOT" getent hosts archive.ubuntu.com 2>&1
    echo "=== step exit codes (name / rc / command)"; cat "$DEBUG_DIR/steps.tsv"
  } > "$DEBUG_DIR/environment.txt" 2>&1
  cat "$ROOT"/etc/apt/sources.list "$ROOT"/etc/apt/sources.list.d/* > "$DEBUG_DIR/sources.txt" 2>&1 || true
  cp -a "$ROOT"/var/log/apt "$DEBUG_DIR/apt-log" 2>/dev/null || true
  cp "$ROOT"/var/log/dpkg.log "$DEBUG_DIR/dpkg.log" 2>/dev/null || true
  chroot "$ROOT" dpkg-query -W -f='${binary:Package}\t${Version}\n' > "$DEBUG_DIR/installed-packages.txt" 2>&1 || true
  for f in "$DEBUG_DIR"/*.log; do
    [ -e "$f" ] || continue
    { echo "===== tail -200 $(basename "$f")"; tail -200 "$f"; } >> "$DEBUG_DIR/tails.txt"
  done
  umount -l "$ROOT/dev" "$ROOT/proc" "$ROOT/sys" 2>/dev/null || true
  echo "== diagnostics written to $DEBUG_DIR"
}
trap collect_debug EXIT

# Package set per variant — the three architectures we are comparing.
BASE="ubuntu-minimal ca-certificates linux-image-generic systemd-sysv casper network-manager pipewire pipewire-pulse wireplumber dolphin konsole dbus-user-session qt6-wayland fonts-dejavu-core python3 python3-pyside6.qtquick python3-pyside6.qtsvg qml6-module-qtquick-controls"
case "$VARIANT" in
  full)     EXTRA="plasma-desktop plasma-workspace kwin-wayland" ;;
  services) EXTRA="kwin-wayland plasma-nm plasma-pa powerdevil kscreen" ;;
  legacy)   EXTRA="kwin-wayland layer-shell-qt" ;;
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

# apt is split into update and install so a failure names which half broke, and both keep full output.
step apt-update chroot "$ROOT" env DEBIAN_FRONTEND=noninteractive apt-get update
echo "== install packages ($VARIANT): $BASE $EXTRA"
step apt-install chroot "$ROOT" env DEBIAN_FRONTEND=noninteractive \
  apt-get install -y --no-install-recommends $BASE $EXTRA

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
# ca-certificates is only a *recommend* of git, and we install with --no-install-recommends, so
# without naming it the chroot has no CA store and every HTTPS clone dies on "Problem with the SSL CA cert".
step theme chroot "$ROOT" sh -c "apt-get install -y --no-install-recommends git sassc ca-certificates gtk-update-icon-cache \
  && /opt/zaldros/theme/fetch-sources.sh /usr/src \
  && /opt/zaldros/theme/install-visual-theme.sh --dest / --variant dark"

case "$VARIANT" in
  # Run #22: full used startplasma-wayland only as a fallback while the shell crashed on a missing
  # PySide6.QtSvg. The spec requires the Zaldros shell in every variant, so full uses it too now.
  full)     SESSION_EXEC="/usr/local/bin/zaldros-session" ;;
  services) SESSION_EXEC="/usr/local/bin/zaldros-session" ;;
  legacy)   SESSION_EXEC="/usr/local/bin/zaldros-session" ;;
esac
cat > "$ROOT/usr/local/bin/zaldros-session" <<'EOS'
#!/bin/sh
# KWin as the compositor, the Zaldros shell as the only shell process. No plasmashell.
export QT_QPA_PLATFORM=wayland PYTHONPATH=/opt/zaldros
# ponytail: the "run" subcommand is required by the shell CLI. Without it argparse exited 2 at
# startup, which is why services/legacy booted to a black screen in run #18.
# Run #19: the shell process was gone by self-test time and the unit journal held nothing about
# it, so capture the session's own output in a file the self-test can read back.
# Run #20: /var/log is not writable by user ubuntu, so the redirect itself made the unit exit 2
# before anything started. /tmp is writable by the session user, so log there.
exec >>/tmp/zaldros-session.log 2>&1
set -x
# Run #23: kwin_wayland re-splits its application argument on spaces, so `sh -c '...'` arrived as
# `sh -c python3 -m zaldros_shell run;` and argparse died on the token "run;". Pass one file path.
exec kwin_wayland --xwayland -- /usr/local/bin/zaldros-shell-run
EOS
chmod +x "$ROOT/usr/local/bin/zaldros-session"
cat > "$ROOT/usr/local/bin/zaldros-shell-run" <<'EOS'
#!/bin/sh
python3 -m zaldros_shell run
echo "zaldros-shell exited $?"
EOS
chmod +x "$ROOT/usr/local/bin/zaldros-shell-run"
# ponytail: no display manager. Run #16 proved sddm never honoured its autologin config and fell
# back to an X greeter that does not exist in this image (no Xorg), so nothing ever started the
# session: kwin=false, no wayland socket, every UI step FAIL. A systemd autologin unit on tty1 is
# the shortest thing that actually starts the session, and it drops sddm's ~25 MiB RSS as well.
cat > "$ROOT/etc/systemd/system/zaldros-session.service" <<EOS
[Unit]
Description=Zaldros desktop session (autologin)
After=systemd-user-sessions.service plymouth-quit.service
Conflicts=getty@tty1.service
[Service]
User=ubuntu
PAMName=login
TTYPath=/dev/tty1
TTYReset=yes
TTYVHangup=yes
StandardInput=tty
StandardOutput=journal
Environment=XDG_SESSION_TYPE=wayland XDG_SEAT=seat0 XDG_CURRENT_DESKTOP=KDE
Environment=XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus
ExecStart=$SESSION_EXEC
Restart=no
[Install]
WantedBy=graphical.target
EOS
chroot "$ROOT" systemctl enable zaldros-session.service
chroot "$ROOT" systemctl set-default graphical.target
# The .desktop entry stays so a display manager can be added later, but nothing depends on it now.
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
ExecStart=/bin/sh -c 'runuser -u ubuntu -- env XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus WAYLAND_DISPLAY=wayland-0 QT_QPA_PLATFORM=wayland /usr/local/bin/zaldros-uitest > /dev/ttyS0 2>/var/log/zaldros-uitest.err'
TimeoutStartSec=600
ExecStopPost=/usr/bin/systemctl poweroff
[Install]
WantedBy=graphical.target
EOS
chroot "$ROOT" systemctl enable zaldros-selftest.service
# It only re-verifies the ISO checksum; it fails on our generated image and holds is-system-running at "starting".
chroot "$ROOT" systemctl mask casper-md5check.service

echo "== squashfs + ISO"
umount -l "$ROOT/dev" "$ROOT/proc" "$ROOT/sys" 2>/dev/null || true; trap - EXIT
install -d "$WORK/iso/casper" "$WORK/iso/boot/grub"
mksquashfs "$ROOT" "$WORK/iso/casper/filesystem.squashfs" -comp zstd -Xcompression-level 15 -noappend
cp "$ROOT"/boot/vmlinuz-* "$WORK/iso/casper/vmlinuz"
cp "$ROOT"/boot/initrd.img-* "$WORK/iso/casper/initrd"
# ponytail: GRUB itself talks to the serial port, so a GRUB-level failure is visible
# in the boot log instead of a black screen (run #14: empty serial log, no evidence).
cat > "$WORK/iso/boot/grub/grub.cfg" <<EOS
serial --unit=0 --speed=115200
terminal_input console serial
terminal_output console serial
set timeout=5
echo "GRUB: Zaldros $VARIANT menu loaded"
menuentry "Zaldros OS ($VARIANT)" {
  echo "GRUB: loading kernel"
  linux /casper/vmlinuz boot=casper console=tty0 console=ttyS0,115200 zaldros.selftest noprompt
  echo "GRUB: loading initrd"
  initrd /casper/initrd
  echo "GRUB: booting"
}
EOS
step grub-mkrescue grub-mkrescue -o "$OUT" "$WORK/iso" -- -volid ZALDROS
# Evidence, not assumption: does this ISO actually carry an EFI El Torito image?
echo "== El Torito catalogue"
xorriso -indev "$OUT" -report_el_torito plain 2>&1 | tail -20 || true
xorriso -indev "$OUT" -find /EFI -type f 2>&1 | head -20 || true
echo "ISO: $OUT ($(du -h "$OUT" | cut -f1))"
