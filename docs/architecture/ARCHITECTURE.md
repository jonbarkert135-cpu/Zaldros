# Zaldros OS — Architecture (Phase 0 baseline)

Derived from spec PART 1 §5 and PART 2. Layer names use the official project naming.

## 1. Layers

```
┌─ User Applications ─────────── Flatpak apps, Wine/Proton apps, distrobox
├─ Zaldros System Applications ─ Files, Settings, Terminal, Task Manager, Store, Update,
│                                Screenshot, Text Editor, Archive Manager
├─ Zaldros Desktop Shell ─────── Taskbar, Start, Search, Quick Settings, Notification Centre,
│                                Desktop/Icons, Run, Clipboard History, Recycle Bin
├─ Display / Compositor ──────── KWin (Wayland) + xwayland, layer-shell, xdg-desktop-portal
├─ Hardware / System Services ── systemd, NetworkManager, PipeWire/WirePlumber, BlueZ,
│                                UPower, iwd/wpa, fwupd, udisks2, CUPS (opt), SELinux
├─ Core System ───────────────── glibc, systemd, bootc/ostree, podman, Flatpak, dbus
└─ Linux Kernel ──────────────── Fedora kernel + firmware, btrfs, zram, io_uring
```

Rule (§5): the core system must boot, update, network and log with the entire shell layer removed.
CI enforces this: the `core` image target is built and booted headless without any Zaldros shell package.

## 2. Technology stack (decisions)

| Area | Decision | Source |
|---|---|---|
| Base | Fedora, bootable-container (bootc) flavour | research/01 |
| Init | systemd (non-negotiable given bootc/ostree, portals, logind) | research/01 |
| Filesystem | btrfs + subvolumes + zstd:1 compression; zram swap; `/usr` read-only | ADR-0004 |
| Display protocol | Wayland (xwayland for legacy) | research/02 |
| Compositor | KWin 6 | research/02 |
| Shell toolkit | Qt 6 / QML | research/02 |
| System-component language | Rust (new daemons/tools), C++ where Qt/KWin integration demands | research/02 |
| System package layer | rpm layered into the OS image at build time (not at runtime) | research/01 |
| User app format | Flatpak (primary), Wine/Proton (Windows apps), distrobox (dev/`.deb`) | research/01 |
| Update system | atomic A/B image update + rollback, Windows-like "update and restart" UX | research/01 |
| Installer | Anaconda/`bootc install` for v0.x; custom Zaldros Setup UI once the shell exists | roadmap |
| Security | SELinux enforcing, read-only `/usr`, Flatpak portals, signed images, LUKS opt-in, TPM-backed unlock | SECURITY.md |
| Windows compat | Wine/Proton as an optional managed component | research/02 |

## 3. Performance profiles (PART 1 §8)

| Profile | Target | Mechanism |
|---|---|---|
| Zaldros Desktop | everyday use | default service set, animations on, balanced CPU governor |
| Zaldros Performance | maximum responsiveness | animations reduced, background indexing off, `performance`/EPP tuning, minimal service set |
| Zaldros Legacy | ≤4 GB RAM / HDD / old GPU | software-friendly effects off, no compositing extras, zram aggressive, reduced-motion default |

Profiles are systemd presets + shell settings, generated from the service map produced by
`tools/zaldros-sysprobe`. No profile may disable a service without an entry in the service map
justifying it (§6, §7).

## 4. Measurement contract

Every profile and every shell milestone reports: boot time (`systemd-analyze`), idle RAM (PSS),
idle CPU %, cold Start-menu open latency, frame timing under a standard window-drag test.
Numbers without a baseline are not accepted as evidence (§6, §15).
