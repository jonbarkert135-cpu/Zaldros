# Zaldros System Applications — plan and build/reuse decisions

Source: spec PART 3. Rule applied throughout (PART 1 §9, PART 3 §24 of PART 2): mature OSS >
compatible OSS > fork > custom. Every GUI must control or inspect **real** Linux functionality —
no fake toggles, no fabricated hardware data, no invented log events (PART 3 §21).

## Decision table

| Zaldros app | Strategy | Basis / real Linux backend | Rationale |
|---|---|---|---|
| **Zaldros Explorer** | **Fork + reskin Dolphin** (KIO, Qt6) | KIO (smb/sftp/mtp), udisks2, `gio trash` | Dolphin already has tabs, breadcrumbs, split view, previews, network locations, trash. Writing a file manager from scratch is a multi-year trap. Our work: Explorer-like layout, ribbonless Win11 command bar, navigation pane presets, default columns/behaviour. |
| **Zaldros Settings** | **Custom (Qt6/QML)** — the flagship differentiator | KDE config APIs, NetworkManager D-Bus, PipeWire, BlueZ, UPower, logind, accountsservice, firewalld, portals | Windows-11 category structure (System / Bluetooth & devices / Network / Personalization / Apps / Accounts / Privacy & security / Update) cannot be reached by re-arranging KDE System Settings. Each page is a thin, honest front-end over a real D-Bus service. |
| **Zaldros Update Center** | Custom UI, thin | apt (system), Flatpak (apps), fwupd (firmware) | Windows-like "check → download → restart to apply". **Rollback is NOT available**: ADR-0009 moved the base off the image model, and the btrfs-snapshot replacement is unbuilt. Never contacts Windows Update. |
| **Zaldros Notepad** | Custom (Qt6, minimal) | plain files, `uchardet` for encodings | §4 demands *extremely fast startup* and low memory; Kate/KWrite carry a plugin framework we do not need. Target: <120 ms cold start, <40 MB RSS. |
| **Zaldros Terminal** | **Reuse Konsole** (Qt6, KDE) + Zaldros profile set | login shells; profiles for bash/zsh/fish and `pwsh` when installed | Konsole has tabs, split panes, profiles, working-directory integration. Custom terminals are a solved problem. |
| PowerShell | Optional Flatpak/rpm of **PowerShell 7 (MIT, cross-platform)** exposed as a Terminal profile | `pwsh` | Legitimate open-source implementation; no proprietary Windows components. Not installed by default — offered in Settings → Apps → Optional features. |
| **Zaldros Task Manager** | Custom (Qt6/QML) | `/proc`, cgroups v2, `netlink`, DRM/`sysfs` GPU counters, systemd D-Bus | Windows-11 layout (Processes / Performance / App history / Startup / Services). Safeguards: SIGTERM before SIGKILL, confirm for system-owned processes, never offer to kill PID 1 / session-critical units. |
| **Zaldros Device Manager** | Custom, read-mostly | `udev`, `hwdata`, `lspci`/`lsusb` libraries, `sysfs`, DRM | Real device tree, real driver/module names — no fabricated Windows device classes. |
| **Zaldros Disk Management** | Custom UI over **udisks2**; delegate risky ops | udisks2, `libblockdev`, btrfs tools | Read-only view is safe by default; partition changes require typed confirmation + a warning about data loss, and are refused on the running root device. |
| **Resource Monitor** | Custom view inside Task Manager binary | same backends + `io_uring`/`bpf` counters where available | Avoids a second always-running process (§ minimalism). |
| **Event Viewer** | Custom UI over **journald** | `sd-journal` API, categorised by unit/priority/facility | Real logs only. Categories map to journald fields, documented in-app so users learn the truth about their system. |
| **Zaldros Services** | Custom UI | systemd D-Bus + the map from `tools/zaldros-sysprobe` | Shows dependants and resource cost — the §7 service map surfaced to users. Only enable/disable/start/stop/restart; masking hidden behind an advanced toggle. |
| **System Information** | Custom, read-only | `sysfs`, DMI/SMBIOS, DRM, PipeWire, `uname`, ostree image version | |
| **Startup Apps** | Custom | XDG autostart, systemd user units | "Impact" is measured (activation time + RSS), never guessed. |
| **Firewall** | Custom UI over **firewalld** | firewalld D-Bus (nftables backend) | Profiles map to Windows-like Private/Public networks. |
| **Zaldros Recovery** | Custom UI + boot-menu entry | btrfs snapshots, `bootctl`, the live ISO as a recovery image | The on-disk recovery entry must be rebuilt on the Ubuntu base (ADR-0009); today only the live ISO can recover a system. |
| Screenshot | **Reuse Spectacle** + Zaldros shortcuts (Win+Shift+S) | xdg-desktop-portal screenshot API | |
| Archive manager | **Reuse Ark** | libarchive, 7zip, zstd | |
| Image viewer / media player / calculator | Reuse gwenview (or a lighter Qt viewer), **mpv**, a Qt calculator | | |
| Browser | **Firefox** (default), Chromium available | | No Edge, no Microsoft binaries. |
| Software centre | Zaldros Store = thin Flatpak front-end | Flatpak/Flathub metadata | |

## Default application set (PART 3 §19)

Browser, Explorer, Notepad, Terminal, Settings, Update Center, Task Manager, Device Manager,
Disk Management, Event Viewer, Services, System Information, Firewall, Recovery, Screenshot,
Archive manager, Image viewer, Media player, Calculator, Store. Nothing else preinstalled —
every addition must justify its RAM, disk and attack surface.

## Quality gates per application (PART 3 §20)

| Gate | Threshold |
|---|---|
| Cold start | Notepad < 120 ms, Explorer < 400 ms, Settings < 500 ms |
| Idle RSS | Notepad < 40 MB, Explorer < 120 MB, Task Manager < 90 MB |
| Background cost when closed | zero resident processes (no app-specific daemons) |
| Accessibility | full keyboard navigation + AT-SPI exposure of all controls |
| Design | one Zaldros design system, no mixed toolkits in a single window |
| Honesty | every displayed value traceable to a real kernel/D-Bus source |

## Sequencing

Phase 3 order (highest user value first): Settings → Explorer → Update Center → Task Manager →
Terminal/Notepad → Device Manager, Services, Event Viewer, System Information → Disk Management,
Firewall, Recovery.
