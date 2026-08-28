#!/bin/sh
# Collect everything needed to debug a Zaldros boot on real hardware, into one archive.
#
# Run it inside a booted Zaldros session (live USB is fine):
#
#     sh /usr/share/zaldros/collect-logs.sh            # or ./tools/collect-logs.sh from a checkout
#
# It prints the path of a .tar.gz at the end. Copy that file off the machine (a USB stick, or the
# Windows partition) and hand it over — it is the difference between "the desktop did not start"
# and knowing which unit failed.
#
# Rules this script follows, because it runs on a machine we cannot see:
#   * never fail as a whole: every probe is guarded, a missing tool is recorded as missing;
#   * never require the network;
#   * never collect secrets: no Wi-Fi keys (nmcli is asked for device status only), no password
#     database, no saved connection files, no browser profiles, no files from home — logs,
#     hardware and unit state only. `tests/test_collect_logs.py` enforces this list.
set -u

OUT_DIR="${1:-${TMPDIR:-/tmp}}"
STAMP="$(date -u +%Y%m%d-%H%M%S 2>/dev/null || echo unknown)"
HOST="$(hostname 2>/dev/null || echo host)"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/zaldros-logs.XXXXXX")" || exit 1
NAME="zaldros-logs-${HOST}-${STAMP}"
DIR="${WORK}/${NAME}"
mkdir -p "${DIR}" || exit 1

# Every probe goes through this: the file always exists, and says why it is empty when it is.
grab() {
    file="${DIR}/$1"
    shift
    if command -v "$1" >/dev/null 2>&1; then
        # stderr is kept: "Failed to get D-Bus connection" is the answer more often than stdout is.
        "$@" >"${file}" 2>&1 || echo "[exit $? from: $*]" >>"${file}"
    else
        echo "[missing tool: $1]" >"${file}"
    fi
    # An empty file is ambiguous to whoever reads the archive: did the probe not run, or did the
    # machine really have nothing to say? `systemctl --failed` on a healthy host prints nothing,
    # and that silence is a *result*. It gets written down as one.
    [ -s "${file}" ] || echo "[no output from: $*]" >"${file}"
}

copy() {
    for path in "$@"; do
        [ -e "${path}" ] || continue
        target="${DIR}/files/$(echo "${path}" | sed 's|^/||; s|/|_|g')"
        mkdir -p "${DIR}/files"
        cp -a "${path}" "${target}" 2>/dev/null || echo "[unreadable]" >"${target}"
    done
}

# -- who and what -----------------------------------------------------------------------------
{
    echo "collected: $(date -u 2>/dev/null) UTC"
    echo "script: collect-logs.sh"
    echo "user: $(id 2>/dev/null)"
    echo "kernel: $(uname -a 2>/dev/null)"
    echo "cmdline: $(cat /proc/cmdline 2>/dev/null)"
    echo "uptime: $(cat /proc/uptime 2>/dev/null)"
    echo "variant: $(cat /etc/zaldros-variant 2>/dev/null || echo unknown)"
    echo "live session: $([ -d /run/live ] && echo yes || echo 'no/unknown')"
    echo "session type: ${XDG_SESSION_TYPE:-unset}, desktop: ${XDG_CURRENT_DESKTOP:-unset}"
    echo "wayland display: ${WAYLAND_DISPLAY:-unset}, runtime dir: ${XDG_RUNTIME_DIR:-unset}"
} >"${DIR}/00-summary.txt" 2>&1
copy /etc/os-release /etc/zaldros-variant /proc/cmdline

# -- the boot itself --------------------------------------------------------------------------
grab 10-journal-boot.log journalctl -b --no-pager
grab 11-journal-priority-warning.log journalctl -b -p warning --no-pager
grab 12-journal-user.log journalctl --user -b --no-pager
grab 13-dmesg.log dmesg
grab 14-systemd-failed.txt systemctl --failed --no-pager --no-legend
grab 15-systemd-jobs.txt systemctl list-jobs --no-pager --no-legend
grab 16-systemd-state.txt systemctl is-system-running
grab 17-systemd-analyze.txt systemd-analyze time
grab 18-systemd-blame.txt systemd-analyze blame --no-pager
for unit in zaldros-session zaldros-selftest sddm display-manager NetworkManager bluetooth; do
    grab "19-unit-${unit}.txt" systemctl status "${unit}" --no-pager -l
done
grab 20-session-journal.log journalctl -b -u zaldros-session --no-pager

# -- the desktop ------------------------------------------------------------------------------
grab 30-processes.txt ps -eo pid,ppid,rss,pcpu,comm,args
grab 31-kwin-journal.log journalctl -b --no-pager -g kwin
grab 32-loginctl.txt loginctl list-sessions --no-pager
grab 33-wayland-sockets.txt sh -c 'ls -la "${XDG_RUNTIME_DIR:-/run/user/$(id -u)}" 2>&1'
grab 34-drm.txt sh -c 'for card in /sys/class/drm/*/status; do echo "$card: $(cat "$card" 2>&1)"; done'

# What the shell itself thinks of this machine — the same readings the tray draws, plus which
# services answered. This is the fastest way to see a facet failing on real hardware.
if command -v python3 >/dev/null 2>&1; then
    python3 - >"${DIR}/35-backend-status.json" 2>&1 <<'PY'
import json
try:
    from zaldros_backend import ZaldrosBackend
except Exception as exc:                                   # noqa: BLE001 - reported, not hidden
    print(json.dumps({"error": f"zaldros_backend not importable: {exc}"}, ensure_ascii=False))
else:
    backend = ZaldrosBackend()
    tray = {key: {"available": r.available, "value": r.value, "detail": r.detail,
                  "source": r.source, "extra": {k: str(v) for k, v in r.extra.items()}}
            for key, r in backend.tray().items()}
    print(json.dumps({"status": backend.status(), "tray": tray}, indent=2, ensure_ascii=False,
                     default=str))
PY
else
    echo "[missing tool: python3]" >"${DIR}/35-backend-status.json"
fi

# -- hardware ---------------------------------------------------------------------------------
grab 40-cpuinfo.txt cat /proc/cpuinfo
grab 41-meminfo.txt cat /proc/meminfo
grab 42-lspci.txt sh -c 'lspci -nnk 2>/dev/null || for d in /sys/bus/pci/devices/*; do
    echo "$d vendor=$(cat "$d/vendor" 2>/dev/null) device=$(cat "$d/device" 2>/dev/null) driver=$(basename "$(readlink "$d/driver" 2>/dev/null)" 2>/dev/null)"; done'
grab 43-usb.txt sh -c 'lsusb 2>/dev/null || ls -1 /sys/bus/usb/devices 2>&1'
grab 44-block.txt sh -c 'lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT 2>&1'
grab 45-network.txt sh -c 'ip -d addr 2>&1; echo; nmcli -t device status 2>&1'
grab 46-audio.txt sh -c 'wpctl status 2>&1; echo; cat /proc/asound/cards 2>&1'
grab 47-input.txt cat /proc/bus/input/devices
grab 48-firmware.txt sh -c 'ls -1 /sys/firmware 2>&1; echo secureboot:; od -An -t u1 /sys/firmware/efi/efivars/SecureBoot-* 2>&1 | tail -1'
grab 49-hwinfo.md python3 -m zaldros_hwinfo
grab 50-sysprobe.md python3 -m zaldros_sysprobe

# -- a picture of the screen ------------------------------------------------------------------
for tool in spectacle grim; do
    command -v "${tool}" >/dev/null 2>&1 || continue
    case "${tool}" in
        spectacle) spectacle -b -n -o "${DIR}/60-screen.png" >/dev/null 2>&1 ;;
        grim) grim "${DIR}/60-screen.png" >/dev/null 2>&1 ;;
    esac
    [ -s "${DIR}/60-screen.png" ] && break
done
[ -s "${DIR}/60-screen.png" ] || echo "no screenshot: neither spectacle nor grim produced one" \
    >"${DIR}/60-screen.missing.txt"

# -- pack -------------------------------------------------------------------------------------
ARCHIVE="${OUT_DIR%/}/${NAME}.tar.gz"
if ! tar -czf "${ARCHIVE}" -C "${WORK}" "${NAME}" 2>/dev/null; then
    echo "could not write ${ARCHIVE}; the collected files are in ${DIR}"
    exit 1
fi
rm -rf "${WORK}"
echo "${ARCHIVE}"
echo "size: $(du -h "${ARCHIVE}" 2>/dev/null | cut -f1)"
echo "Copy this file off the machine and send it over."
