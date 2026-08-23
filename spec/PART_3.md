# RAVEN OS (→ Bedrock Linux) — MASTER SPECIFICATION — PART 3/5 — SYSTEM APPLICATIONS & WINDOWS-LIKE UTILITIES
Received 2026-08-23 (Slack DM). Combine with PART 1 and PART 2. Naming: see docs/NAMING.md ("Raven" → "Bedrock").

1. BEDROCK EXPLORER — full file manager: drives, folders, files, navigation pane, address bar, breadcrumbs, search, tabs, sorting, grouping, thumbnails, previews, properties, context menus, copy/move/rename/delete, drag-and-drop, multi-selection, clipboard, archives, removable devices, network locations, file associations, recycle bin. Use real Linux filesystem semantics; do NOT fake Windows drive letters; present Linux filesystems in a friendly way.
2. FILE ASSOCIATIONS — default app handling (.txt → Notepad, images → viewer, video → player, archives → archive manager, URLs → browser); user-changeable.
3. BEDROCK SETTINGS — Windows-familiar structure:
   - SYSTEM: Display, Sound, Notifications, Power, Storage, Multitasking, Recovery, Clipboard, Remote Desktop (where supported), About.
   - BLUETOOTH & DEVICES: Bluetooth, printers, mouse, keyboard, touchpad, USB, cameras, other peripherals.
   - NETWORK & INTERNET: Wi-Fi, Ethernet, VPN, proxy, DNS, firewall, network info.
   - PERSONALIZATION: background, colours, themes, lock screen, Start, taskbar, fonts, appearance.
   - APPS: installed apps, default apps, optional features, startup apps, app permissions.
   - ACCOUNTS: users, login, authentication, permissions, account management.
   - PRIVACY & SECURITY: privacy, app/camera/microphone/location permissions, firewall, security status.
   - UPDATES — Bedrock Update Center: update checking, package updates, security updates, history, rollback where possible, reboot requirements, scheduling. Never connect to Windows Update.
4. BEDROCK NOTEPAD — lightweight editor: extremely fast startup, plain text, tabs, search, replace, encoding selection, line endings, recent files, file associations, shortcuts, autosave where appropriate.
5. BEDROCK TERMINAL — multiple shells (investigate Bash, Zsh, Fish, PowerShell); tabs, split panes, profiles, custom fonts, colours, copy/paste, shortcuts, configurable shell, working-directory integration.
6. POWERSHELL — investigate legitimate cross-platform PowerShell and integrate as a Terminal profile if appropriate. No proprietary Windows PowerShell components.
7. BEDROCK TASK MANAGER — real Linux resources: processes, CPU, RAM, GPU, disk, network, applications, uptime, services. Safe operations: terminate, inspect, sort by usage, startup management. No dangerous low-level operations without safeguards.
8. BEDROCK DEVICE MANAGER — real hardware via Linux interfaces: CPU, GPU, RAM, storage, USB, audio, network adapters, Bluetooth, cameras, displays, keyboard, mouse, touchpad. No fabricated Windows-specific information.
9. BEDROCK DISK MANAGEMENT — safe GUI: disks, partitions, filesystem info, mount points, storage usage, removable drives; partition operations only where technically safe; dangerous operations require explicit confirmation.
10. RESOURCE MONITOR — deeper than Task Manager: CPU, memory, disk I/O, network, GPU, processes.
11. EVENT VIEWER — friendly view over real Linux logs: system, applications, hardware, security, services, boot, kernel. No invented Windows events.
12. BEDROCK SERVICES — inspect services: name, description, status, startup behaviour, dependencies, resource info. Only safe modifications.
13. BEDROCK SYSTEM INFORMATION — OS, kernel, CPU, GPU, RAM, storage, motherboard, firmware, displays, network, audio, desktop version.
14. STARTUP APPS — GUI: application, startup status, measured impact where possible, location, disable. Never auto-disable critical system services.
15. FIREWALL — friendly GUI driving the real Linux firewall architecture chosen in Phase 0.
16. BEDROCK RECOVERY — system restore strategy, rollback, recovery environment, boot repair, safe mode equivalent, reset/reinstall where practical. Do not pretend Linux mechanisms are Windows mechanisms internally; expose equivalents through a familiar interface.
17. SCREEN CAPTURE — shortcuts, full screen, region, window, clipboard, save.
18. ARCHIVE SUPPORT — open, extract, create, add files, remove files; common formats.
19. DEFAULT SYSTEM APPLICATIONS — sensible default set (browser, file manager, text editor, terminal, media player, image viewer, archive manager, calculator, screenshot tool, system monitor, settings, software centre). Every default must have a clear purpose; avoid unnecessary preinstalled software.
20. APPLICATION QUALITY — priority order: startup speed, low memory, reliability, native integration, accessibility, consistent Bedrock design.
21. ACCEPTANCE CRITERIA — the user must not need separate Linux admin tools; system management is exposed through Bedrock's own interfaces; every GUI controls or inspects real Linux functionality. No fake controls, no fake hardware info, no fake system states.

This is PART 3 OF 5. Preserve requirements; PARTS 4 and 5 pending.
