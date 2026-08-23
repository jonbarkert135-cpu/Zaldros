# Windows → Bedrock feature matrix

Required by spec PART 5 §18. Statuses: **IMPLEMENTED** / **PARTIALLY IMPLEMENTED** /
**ALTERNATIVE IMPLEMENTATION** / **NOT IMPLEMENTED** / **NOT APPLICABLE**.
"Never hide limitations." Today nothing is implemented — the honest matrix is the planning baseline,
and the Status column moves only when a test exists.

| Windows capability | Bedrock implementation | Status | Test | Notes |
| --- | --- | --- | --- | --- |
| Taskbar (pinned, running, previews, tray, clock) | Bedrock Taskbar (Qt6/QML, layer-shell) | NOT IMPLEMENTED | — | Phase 4 |
| Start menu + pinned/recommended | Bedrock Start | NOT IMPLEMENTED | — | Phase 4 |
| Search (apps, files, settings, web) | Bedrock Search over an indexer | NOT IMPLEMENTED | — | Phase 4; indexer must be measurable/disable-able |
| File Explorer | Files (Dolphin fork, Explorer layout) | NOT IMPLEMENTED | — | Phase 5 |
| Settings app | Bedrock Settings (Win11 category tree) | NOT IMPLEMENTED | — | Phase 6 |
| Task Manager | Bedrock Task Manager | NOT IMPLEMENTED | — | Phase 7 |
| Device Manager | Bedrock Device Manager (`bedrock-hwinfo` backend) | PARTIALLY IMPLEMENTED | `tools/bedrock-hwinfo` unit tests | Backend exists, no GUI |
| Services / Event Viewer / Resource Monitor | systemd + journald front-ends (`bedrock-sysprobe`) | PARTIALLY IMPLEMENTED | `tools/bedrock-sysprobe` unit tests | Backend exists, no GUI |
| Windows Update | Bedrock Update Center (bootc atomic + rollback) | NOT IMPLEMENTED | — | Never contacts Windows Update |
| Windows Defender | SELinux + firewalld + Flatpak sandboxing | ALTERNATIVE IMPLEMENTATION | — | No AV product; posture differs by design |
| BitLocker | LUKS2 | ALTERNATIVE IMPLEMENTATION | — | Default-on pending decision |
| Registry | Config files + KConfig/dconf | NOT APPLICABLE | — | No registry equivalent; Settings is the UI |
| .exe installers | Wine/Proton bottles (optional layer) | NOT IMPLEMENTED | — | Phase 9; never promise 100 % |
| Microsoft Store | Bedrock Store (Flatpak/AppImage) | NOT IMPLEMENTED | — | Phase 8 |
| PowerShell | PowerShell 7 (MIT) as an optional Terminal profile | NOT IMPLEMENTED | — | Windows-only modules will not work |
| NTFS/exFAT external drives | kernel ntfs3 + exfat + udisks2 | NOT IMPLEMENTED | — | Untested (`hardware.json`) |
| Snap layouts / virtual desktops / Alt+Tab | KWin rules + Bedrock shell | NOT IMPLEMENTED | — | Phase 4 |
| Windows Hello | fprintd / howdy-style (optional) | NOT IMPLEMENTED | — | Hardware dependent |
| HDR / per-monitor DPI | KWin Wayland capabilities | PARTIALLY IMPLEMENTED (upstream) | — | Known deviation area, R-4 |
