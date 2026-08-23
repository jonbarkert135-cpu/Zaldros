# ZALDROS OS — MASTER SPECIFICATION — PART 2/5 — WINDOWS-LIKE DESKTOP & USER EXPERIENCE
Received 2026-08-23 (Slack DM, Linussi Fril). Combine with PART 1. No full implementation until all 5 parts.

Extra input from user: use official docs as reference — https://learn.microsoft.com/ru-ru/windows/resources/ (download parameter sets / UX guidance and follow them precisely). Reference screenshot of Windows 11 desktop + Start menu (RU locale, dark Start, centered taskbar) supplied as UX reference.

1. WINDOWS 11 PARITY — not only visuals: layout, interaction patterns, workflows, keyboard shortcuts, navigation, system controls, window management, file management, settings organization, notifications, app launching. Each common Windows feature → equivalent, better Linux-native version with same workflow, or documented alternative.
2. DESKTOP — wallpaper, icons, shortcuts, folders, files, right-click menu, refresh, display settings, personalization, drag-and-drop, multi-monitor, virtual desktops.
3. TASKBAR — Start button, search, pinned + running apps, previews, system tray, network, volume, Bluetooth, battery, clock, notifications, quick settings, calendar; auto-hide, customization, grouping, multi-monitor, keyboard nav, taskbar settings.
4. START MENU (Zaldros Start) — pinned apps, all installed apps, recent items, search, user profile, power, settings, system shortcuts, keyboard nav. Must open fast; no heavy always-on indexer unless justified.
5. SEARCH — global: apps, files, folders, settings, commands, system tools, installed packages. Resource-efficient, index only what's necessary.
6. WINDOW MANAGEMENT — minimize/maximize/close/resize, snap, side-by-side, drag-to-maximize, virtual desktops, multi-monitor, Alt+Tab, keyboard nav; reproduce modern Windows workflow with Linux-native tech.
7. KEYBOARD SHORTCUTS — Win, Win+E/R/I/S/Tab, Alt+Tab, Ctrl+C/V/X/Z, Ctrl+Shift+Esc; don't break important Linux conventions.
8. SYSTEM TRAY — real tray: network, Wi-Fi, Ethernet, sound, Bluetooth, battery, notifications, background apps, clock, quick settings. Indicators must reflect real state.
9. QUICK SETTINGS — Wi-Fi, Bluetooth, airplane mode, volume, brightness, power, VPN, night light, accessibility, project/screen. No fake toggles — each must drive the real Linux subsystem.
10. NOTIFICATIONS — app + system notifications, history, Do Not Disturb, permissions, priority behaviour.
11. CALENDAR/CLOCK — date, time, calendar panel, timezone, localization, 12/24h.
12. RUN — Windows-like Run dialog: apps, commands, paths, URLs, system utilities.
13. RECYCLE BIN — delete, restore, permanent delete, empty, per-volume handling.
14. CLIPBOARD — text, images, history where practical, shortcuts, secure handling.
15. SCREENSHOTS — fullscreen, region, window, to clipboard, to file, shortcuts.
16. MULTI-MONITOR — displays, resolution, refresh rate, scaling, orientation, primary, arrangement, wallpaper, taskbar behaviour, moving windows.
17. VIRTUAL DESKTOPS — create, delete, switch, name, move apps, shortcuts, overview.
18. THEMING — unified Zaldros design system: typography, spacing, colours, icons, borders, shadows, transparency, controls, menus, dialogs, animations. No mixed visual systems.
19. ANIMATIONS — subtle, modern; PERFORMANCE > ANIMATION. Modes: normal, performance, reduced-motion, disabled.
20. ACCESSIBILITY — scaling, keyboard nav, high contrast, large cursor, font scaling, reduced motion, screen reader where practical, accessibility permissions.
21. VISUAL REGRESSION TESTING — REFERENCE → IMPLEMENTATION → SCREENSHOT → VISUAL COMPARISON → DEVIATION ANALYSIS → CORRECTION → RETEST. Compare geometry, spacing, typography, icon placement, colours, transparency, shadows, borders, animation. Maintain internal visual similarity score.
22. UX REQUIREMENT — Windows user does normal tasks without Linux knowledge (Start, app search, Explorer, Settings, Wi-Fi, sound, install app, terminal, files, display settings, Bluetooth, multi-display, update).
23. DESIGN PRINCIPLE — not "Linux with a Windows theme" but "a complete Linux desktop environment designed around Windows-familiar workflows".
24. IMPLEMENTATION PRINCIPLE — research existing OSS first; integrate/adapt/fork/theme/extend before custom.
25. ACCEPTANCE — visual comparison, interaction comparison, shortcut tests, multi-monitor tests, accessibility tests, performance tests, regression tests. Screenshots alone never mark it complete.

Reference asset saved: refs/win11_start_reference.png
