# Windows → Zaldros feature matrix

Required by spec PART 5 §18. Statuses: **IMPLEMENTED** / **PARTIALLY IMPLEMENTED** /
**ALTERNATIVE IMPLEMENTATION** / **NOT IMPLEMENTED** / **NOT APPLICABLE**.
"Never hide limitations." Today nothing is implemented — the honest matrix is the planning baseline,
and the Status column moves only when a test exists.

| Windows capability | Zaldros implementation | Status | Test | Notes |
| --- | --- | --- | --- | --- |
| Taskbar (pinned, running, previews, tray, clock) | Zaldros Taskbar (Qt6/QML, layer-shell) | NOT IMPLEMENTED | — | Phase 4 |
| Start menu + pinned/recommended | Zaldros Start | NOT IMPLEMENTED | — | Phase 4 |
| Search (apps, files, settings, web) | Zaldros Search over an indexer | NOT IMPLEMENTED | — | Phase 4; indexer must be measurable/disable-able |
| File Explorer | Files (Dolphin fork, Explorer layout) | NOT IMPLEMENTED | — | Phase 5 |
| Settings app | Zaldros Settings (Win11 category tree) | NOT IMPLEMENTED | — | Phase 6 |
| Task Manager | Zaldros Task Manager | NOT IMPLEMENTED | — | Phase 7 |
| Device Manager | Zaldros Device Manager (`zaldros-hwinfo` backend) | PARTIALLY IMPLEMENTED | `tools/zaldros-hwinfo` unit tests | Backend exists, no GUI |
| Services / Event Viewer / Resource Monitor | systemd + journald front-ends (`zaldros-sysprobe`) | PARTIALLY IMPLEMENTED | `tools/zaldros-sysprobe` unit tests | Backend exists, no GUI |
| Windows Update | Zaldros Update Center (bootc atomic + rollback) | NOT IMPLEMENTED | — | Never contacts Windows Update |
| Windows Defender | SELinux + firewalld + Flatpak sandboxing | ALTERNATIVE IMPLEMENTATION | — | No AV product; posture differs by design |
| BitLocker | LUKS2 | ALTERNATIVE IMPLEMENTATION | — | Default-on pending decision |
| Registry | Config files + KConfig/dconf | NOT APPLICABLE | — | No registry equivalent; Settings is the UI |
| .exe installers | Wine/Proton bottles (optional layer) | NOT IMPLEMENTED | — | Phase 9; never promise 100 % |
| Microsoft Store | Zaldros Store (Flatpak/AppImage) | NOT IMPLEMENTED | — | Phase 8 |
| PowerShell | PowerShell 7 (MIT) as an optional Terminal profile | NOT IMPLEMENTED | — | Windows-only modules will not work |
| NTFS/exFAT external drives | kernel ntfs3 + exfat + udisks2 | NOT IMPLEMENTED | — | Untested (`hardware.json`) |
| Snap layouts / virtual desktops / Alt+Tab | KWin rules + Zaldros shell | NOT IMPLEMENTED | — | Phase 4 |
| Windows Hello | fprintd / howdy-style (optional) | NOT IMPLEMENTED | — | Hardware dependent |
| HDR / per-monitor DPI | KWin Wayland capabilities | PARTIALLY IMPLEMENTED (upstream) | — | Known deviation area, R-4 |
