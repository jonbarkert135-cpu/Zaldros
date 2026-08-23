# ZALDROS OS (→ Zaldros Linux) — MASTER SPECIFICATION — PART 4/5 — APPLICATIONS, COMPATIBILITY, HARDWARE & SECURITY
Received 2026-08-23 (Slack DM). Combine with PARTS 1–3. Naming: see docs/NAMING.md.

1. APPLICATION INSTALLATION — make installing apps easy for non-Linux users; research/integrate native packages, Flatpak, AppImage, distro repos, Wine-based apps, other formats. Do not expose package-management complexity unnecessarily.
2. ZALDROS SOFTWARE CENTER — unified app management: search, categories, app pages, screenshots, install, uninstall, update, permissions, storage usage, source information. Architecture must respect the real package formats underneath.
3. WINDOWS APPLICATION COMPATIBILITY — research Wine, Proton, Bottles, other legitimate tech. Optional compatibility layer. Never promise 100 % compatibility. Classify apps: Native Linux / Compatible / Partially Compatible / Unsupported, based on testing where possible.
4. WINDOWS GAMES — research Proton, Vulkan, GPU drivers, controller support, launchers, shader caching, compatibility tools. Never compromise system stability for gaming.
5. BROWSER — modern default browser (tabs, bookmarks, history, downloads, profiles, extensions, privacy controls, password management, hardware acceleration). No proprietary browser source copying. Other browsers installable.
6. HARDWARE SUPPORT — Intel/AMD CPUs; NVIDIA/AMD/Intel GPUs; Wi-Fi, Ethernet, Bluetooth, USB, webcams, microphones, speakers, headphones, printers, touchpads, keyboards, controllers, external displays. Do NOT remove drivers merely for performance.
7. GPU — hardware acceleration whenever available; investigate Vulkan, OpenGL, the Linux graphics stack, NVIDIA proprietary drivers where necessary, Mesa, Wayland/X11. Choose on current hardware support and long-term maintainability.
8. AUDIO — speakers, headphones, microphones, Bluetooth audio, volume, per-application volume, input/output selection; modern Linux audio architecture.
9. NETWORKING — friendly UI for Wi-Fi, Ethernet, VPN, DNS, proxy, hotspot; taskbar must reflect the true network state.
10. BLUETOOTH — pairing, disconnect, remove, battery status where available, audio profiles, input devices.
11. POWER MANAGEMENT — battery, charging, suspend, hibernate where hardware permits, screen timeout, sleep, performance/balanced/power-saving modes, lid behaviour. Measure power consumption.
12. BATTERY OPTIMIZATION — research Linux power management; never apply aggressive settings blindly; measure idle, screen-on, sleep consumption, CPU and GPU behaviour.
13. SECURITY — privilege separation, sandboxing, firewall, package signature verification, secure updates, permissions, application isolation, secure defaults, minimal network exposure.
14. TELEMETRY — no unnecessary telemetry; anything present must be documented, purposeful, minimal and user-controlled. System must work without cloud dependency.
15. UPDATE SYSTEM — signed packages, secure transport, verification, atomic/transactional updates where practical, rollback strategy, update history, recovery from failed updates.
16. RECOVERY — a failed update must never leave an unusable machine; implement rollback/recovery.
17. PRIVACY — clear privacy UI controlling camera, microphone, location, application permissions, network services, background services.
18. FILESYSTEM — choose on evidence: performance, reliability, snapshots, recovery, SSD and HDD behaviour, encryption, maintenance. Not by popularity.
19. STORAGE — NVMe, SATA SSD, HDD, USB storage, removable media, NTFS, exFAT, FAT and Linux filesystems; users must be able to read common Windows-formatted external drives.
20. INSTALLER — polished GUI installer: disk selection, partitioning, encryption, user creation, timezone, keyboard layout, language, bootloader, network, optional software, installation profile. Safe; destructive operations require explicit confirmation.
21. FIRST BOOT — boot, login, desktop, hardware detection, network, audio, display, updates, basic onboarding. Avoid unnecessary startup applications.
22. FIRST-RUN EXPERIENCE — short optional setup: language, theme, performance profile, privacy settings, default browser, optional compatibility layer, update preferences. Do not overwhelm.
23. WINDOWS MIGRATION — investigate importing browser bookmarks, files, wallpapers, basic preferences, selected application data. Never copy proprietary application binaries.
24. SYSTEM RELIABILITY — survive application crashes, service failures, network failures, interrupted updates, removable-drive disconnection, unexpected termination. An application crash must not take down the desktop.
25. ACCEPTANCE CRITERIA — test on real hardware wherever possible; track compatibility as TESTED / PARTIALLY TESTED / UNTESTED / KNOWN ISSUE. Never claim universal hardware compatibility without evidence.

This is PART 4 OF 5.
