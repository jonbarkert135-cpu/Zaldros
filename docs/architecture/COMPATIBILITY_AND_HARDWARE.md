# Applications, compatibility, hardware, power and security

Source: spec PART 4. Governing rule (§25): compatibility is a *claim*, and a claim without a recorded
test is forbidden. Every statement below is either a decision or a hypothesis marked as untested.

## 1. Application delivery (§1, §2)

| Format | Role in Bedrock | Reason |
|---|---|---|
| **Flatpak** | primary format for user applications | vendor-neutral, sandboxed via portals, works on an image-based OS without touching `/usr` |
| rpm layered in the image | system components only, at build time | keeps `/usr` reproducible (ADR-0001) |
| AppImage | supported, integrated on first launch (desktop entry + updates via AppImageUpdate) | users receive them from vendors; refusing them would break the "just install it" promise |
| distrobox/toolbox container | `.deb`-only and developer tooling | isolates foreign packages from the base image |
| Wine/Proton bottle | Windows applications | see §3 below |

**Bedrock Store** is a thin front-end: search, categories, app pages with screenshots from AppStream
metadata, install/uninstall/update, permission editing (portal permissions per app), storage usage and
— mandatory — the **source** of every app (Flathub / Bedrock repo / AppImage vendor / Wine bottle).
Package-manager vocabulary never appears in the default UI; it is available in an "advanced" view.

## 2. Windows application compatibility (§3, §4)

Optional component, installed on demand (First-run experience or Store), never part of the base image.
Stack: **Wine + Proton (via a Bottles-style managed prefix service) + DXVK/VKD3D + Vulkan**.

Compatibility classes are stored in a machine-readable registry (`compat/registry.json`) and shown in
the Store exactly as recorded:

| Class | Meaning | Evidence required |
|---|---|---|
| Native Linux | a real Linux build exists | package exists |
| Compatible | installs and runs, no blocking defects | a recorded test run on a Bedrock build |
| Partially Compatible | runs with documented limitations | recorded test + description of the limitation |
| Unsupported | does not run, or anti-cheat/DRM blocks it | recorded test or upstream statement |

No application may be shown as Compatible without a test record. Gaming: Proton + Mesa/RADV or NVIDIA
driver, shader cache pre-warm, controller support via `hid`/Steam Input. Stability rule: gaming
components never modify the base image; they live in Flatpak/containers.

## 3. Hardware (§6, §7)

- **Do not remove drivers for performance** (§6). Kernel modules stay in the image; the performance
  profiles may only change *runtime* behaviour (services, polling, animations), never driver presence.
- Graphics: **Mesa** (Intel/AMD, RADV/ANV) by default; **NVIDIA proprietary driver** offered as an
  image variant plus firmware, because Wayland/NVIDIA works acceptably only on recent driver branches —
  status **UNTESTED** in Bedrock until we run the matrix.
- Audio: **PipeWire + WirePlumber** (per-application volume, Bluetooth profiles, low latency,
  PulseAudio/JACK compatibility).
- Networking: **NetworkManager** (Wi-Fi, Ethernet, VPN plugins, DNS, proxy, hotspot); taskbar state
  comes from NetworkManager's D-Bus signals only — never from a poll-and-guess heuristic.
- Bluetooth: **BlueZ** (pairing, profiles, input devices; battery via `upower`/BAP where the device
  reports it — displayed only when actually reported).
- Printers: CUPS + IPP Everywhere driverless; scanners via SANE (optional feature).

Hardware claims are tracked in `hardware/matrix.json` with the four states from §25 and validated in CI
by `tools/bedrock-compat`.

## 4. Power (§11, §12)

Baseline first, tuning second. Defaults: `power-profiles-daemon` (performance / balanced /
power-saver) mapped to the three Bedrock profiles; suspend-to-idle or S3 per firmware capability;
hibernate offered only when a suitable swap target exists and the firmware supports resume.
Measurements required before any tuning ships: idle (screen off), screen-on idle, sleep drain per hour,
CPU package power, GPU power. `tlp`-style aggressive tuning is **not** applied blindly (§12).

## 5. Security posture (§13, §14, §17)

Already decided in `SECURITY.md`; PART 4 adds:
- Package/image signature verification is mandatory and non-optional in the update path.
- Minimal network exposure: no listening services in the default image except what the desktop needs;
  firewalld default zone blocks inbound; SSH is off by default.
- **Telemetry: none.** No analytics, no phone-home, no cloud account requirement. If diagnostics are
  ever added they will be local, opt-in, inspectable and documented here — otherwise this section stays
  as it is.
- Privacy UI drives real portal permissions (camera, microphone, location, screen capture) plus
  service toggles; a permission shown as "off" must be enforced by the portal, not just hidden in the UI.

## 6. Filesystem and storage (§18, §19)

btrfs + zstd:1 (ADR-0004) — chosen for snapshots/rollback and compression on slow disks, **pending
measurement against ext4** (CPU cost, latency on NVMe) before Phase 2 sign-off; that measurement is the
evidence §18 demands. Removable and Windows-formatted media: NTFS via `ntfs3` (kernel), exFAT and FAT
via kernel drivers, auto-mounted through udisks2 so external Windows drives "just work".

## 7. Installer and first run (§20, §21, §22)

- v0.x: `bootc install` / Anaconda kickstart to get bootable media quickly.
- v1: **Bedrock Setup** — language, keyboard, timezone, disk selection with a clear "this erases X"
  confirmation typed by the user, optional LUKS2 encryption, user creation, bootloader, network,
  optional software, installation profile (Desktop / Performance / Legacy).
- First boot must reach the desktop with no startup applications beyond the shell; the optional
  first-run wizard asks at most seven questions (§22) and can be skipped entirely.

## 8. Windows migration (§23)

Bedrock Migration Assistant (Phase 4): mounts the Windows partition read-only and imports browser
bookmarks/history (Firefox/Chrome profile formats), user files, wallpapers, and basic preferences
(timezone, locale, accent colour). It never copies application binaries, fonts or system files.

## 9. Reliability (§24)

- Shell components run as separate processes under systemd user units with `Restart=on-failure`, so a
  taskbar or Start-menu crash restarts in place instead of taking down the session.
- Interrupted update = no change: the running deployment is untouched until the atomic switch.
- Removable-drive disconnection is handled by udisks2 events; Explorer must not block on dead mounts.
- Reliability tests (crash injection per component) become part of the regression suite in Phase 2.
