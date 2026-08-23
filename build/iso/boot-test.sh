#!/usr/bin/env bash
# Boot an ISO in QEMU under UEFI, wait for the in-guest self-test, capture serial log + screenshot.
# A successful build is NOT a successful boot: this script is the only thing that may say PASS.
# Usage: ./boot-test.sh <iso> <profile: low|mid|modern> <results-dir>
set -euo pipefail
ISO="${1:?iso}"; PROFILE="${2:-mid}"; OUT="${3:-results}"
NAME="$(basename "${ISO%.iso}")-$PROFILE"
mkdir -p "$OUT"
# ponytail: never leave results/ empty — an empty dir made the publish step fail too.
trap 'rc=$?; [ "$rc" = 0 ] || echo "boot-test.sh exited $rc" > "$OUT/$NAME.error.txt"' EXIT
SERIAL="$OUT/$NAME.serial.log"; SHOT="$OUT/$NAME.png"; JSON="$OUT/$NAME.json"

case "$PROFILE" in
  low)    CPUS=2; RAM=4096;  VGA=std ;;      # weak graphics: no virtio-gpu acceleration
  mid)    CPUS=4; RAM=8192;  VGA=virtio ;;
  modern) CPUS=8; RAM=16384; VGA=virtio ;;
  *) echo "unknown profile $PROFILE" >&2; exit 2 ;;
esac

# ponytail: plain globbing — `$(ls ... | head -1)` died under `set -e -o pipefail`
# before the check below could report BLOCKED (run #12: exit 2, zero output).
OVMF=""
for c in /usr/share/OVMF/OVMF_CODE_4M.fd /usr/share/OVMF/OVMF_CODE.fd \
         /usr/share/OVMF/OVMF_CODE.4m.fd /usr/share/ovmf/OVMF.fd \
         /usr/share/qemu/OVMF.fd /usr/share/edk2/x64/OVMF_CODE.4m.fd; do
  [ -f "$c" ] && { OVMF="$c"; break; }
done
# last resort: whatever OVMF code file the distro actually shipped
[ -n "$OVMF" ] || OVMF="$(find /usr/share -maxdepth 3 -name 'OVMF_CODE*.fd' -o -maxdepth 3 -name 'OVMF.fd' 2>/dev/null | head -1 || true)"
[ -n "$OVMF" ] || { { ls -l /usr/share/OVMF /usr/share/ovmf 2>&1 || true; } | head -40 >&2; echo "BLOCKED — ENVIRONMENT LIMITATION: no OVMF firmware, UEFI boot untestable" >&2; exit 3; }
ACCEL=tcg; [ -w /dev/kvm ] && ACCEL=kvm
echo "== $NAME: $CPUS vCPU, $RAM MiB, vga=$VGA, accel=$ACCEL"

START=$(date +%s)
timeout "${BOOT_TIMEOUT:-900}" qemu-system-x86_64 \
  -machine q35,accel=$ACCEL -cpu max -smp "$CPUS" -m "$RAM" \
  -drive if=pflash,format=raw,readonly=on,file="$OVMF" \
  -cdrom "$ISO" -boot d -vga "$VGA" -display none \
  -serial "file:$SERIAL" -qmp "unix:$OUT/$NAME.qmp,server,nowait" \
  -no-reboot &
QEMU=$!

# Early screenshot: if the firmware/GRUB stage dies we need a picture of *that*, not of a
# black screen two minutes later.
( sleep "${EARLY_SHOT_DELAY:-25}"
  printf '{"execute":"qmp_capabilities"}\n{"execute":"screendump","arguments":{"filename":"%s"}}\n' \
    "$(readlink -f "$OUT")/$NAME.early.ppm" | timeout 30 socat - "UNIX-CONNECT:$OUT/$NAME.qmp" >/dev/null 2>&1
  [ -f "$OUT/$NAME.early.ppm" ] && command -v convert >/dev/null && convert "$OUT/$NAME.early.ppm" "$OUT/$NAME.early.png" || true ) &

# Screenshot once the desktop has had time to come up; QMP screendump works headless.
( sleep "${SHOT_DELAY:-120}"
  printf '{"execute":"qmp_capabilities"}\n{"execute":"screendump","arguments":{"filename":"%s"}}\n' \
    "$(readlink -f "$OUT")/$NAME.ppm" | timeout 30 socat - "UNIX-CONNECT:$OUT/$NAME.qmp" >/dev/null 2>&1
  [ -f "$OUT/$NAME.ppm" ] && command -v convert >/dev/null && convert "$OUT/$NAME.ppm" "$SHOT" || true ) &

# Stage 2: once the guest reports stage 1, drive the UI over QMP while the VM is still alive.
( for _ in $(seq 1 "${UI_WAIT:-600}"); do
    grep -q 'ZALDROS-SELFTEST {' "$SERIAL" 2>/dev/null && break; sleep 1
  done
  python3 "$(dirname "$0")/ui-drive.py" "$OUT/$NAME.qmp" --out "$OUT" --name "$NAME" \
    >"$OUT/$NAME.ui-drive.log" 2>&1 || echo "UI drive failed, see $OUT/$NAME.ui-drive.log" ) &

wait "$QEMU" && RC=0 || RC=$?
ELAPSED=$(( $(date +%s) - START ))

# The self-test line is the evidence; without it the boot failed, whatever QEMU's exit code says.
# ponytail: the marker is not always at the start of a line — run #15 printed it right after
# getty's "ubuntu login: " prompt, so an anchored grep called a real boot a FAIL.
if grep -q 'ZALDROS-SELFTEST {' "$SERIAL" 2>/dev/null; then
  grep -o 'ZALDROS-SELFTEST {.*' "$SERIAL" | tail -1 | cut -c18- > "$JSON"
  grep -o 'ZALDROS-UITEST {.*' "$SERIAL" | tail -1 | cut -c16- > "$OUT/$NAME.ui-guest.json" 2>/dev/null || true
  python3 - "$JSON" "$ELAPSED" "$PROFILE" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
data["wall_seconds"] = int(sys.argv[2]); data["profile"] = sys.argv[3]; data["boot"] = "PASS"
for extra, key in ((sys.argv[1].replace(".json", ".ui-guest.json"), "ui_guest"),
                   (sys.argv[1].replace(".json", "-host.json"), "ui_host")):
    try:
        data[key] = json.load(open(extra))
    except Exception as exc:
        data[key] = {"status": "MISSING", "why": str(exc)}
json.dump(data, open(sys.argv[1], "w"), ensure_ascii=False, indent=2)
PY
  echo "PASS: $JSON"
else
  python3 -c 'import json,sys; json.dump({"profile":sys.argv[1],"boot":"FAIL","wall_seconds":int(sys.argv[2]),"qemu_rc":int(sys.argv[3]),"serial_tail":open(sys.argv[4],errors="replace").read()[-4000:]},open(sys.argv[5],"w"),ensure_ascii=False,indent=2)' \
    "$PROFILE" "$ELAPSED" "$RC" "$SERIAL" "$JSON"
  echo "FAIL: no self-test marker on the serial log — see $SERIAL"
fi
