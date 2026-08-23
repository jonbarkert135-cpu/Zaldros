# Windows 11 ↔ Bedrock OS parity

(Requested as `WINDOWS_RAVEN_PARITY.md`; renamed to match the official project name — see `docs/NAMING.md`.)

Status values: COMPLETE / PARTIAL / PROTOTYPE / BACKEND ONLY / MISSING / NOT APPLICABLE.
**Working?** and **Tested?** are separate columns on purpose: something can render and still be untested,
and something can be tested and still be useless to a user. Similarity is rated 0–5, and is only filled
in where a real frame exists to compare against the reference screenshot.

| Windows feature | Bedrock implementation | Status | Working? | Tested? | Visual | Behaviour | Known limitations | Priority |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Desktop + wallpaper | QML gradient desktop | PROTOTYPE | yes (rendered) | yes (render test) | 3 | 2 | no icons, no right-click menu, not a session | P2 |
| Taskbar | Bedrock Taskbar (QML) | PROTOTYPE | yes (rendered) | yes | 4 | 3 | window, not a layer-shell panel; no real window list; no previews | P1 |
| Start menu | Bedrock Start (QML) | PROTOTYPE | yes (rendered) | yes | 4 | 2 | pinned list is placeholder JSON; no "All apps"; launches nothing | P1 |
| Taskbar clock | real locale-formatted system clock | PARTIAL | yes | yes | 4 | 4 | no calendar flyout | P3 |
| Running-app indicator | underline driven by real `/proc` process table | PARTIAL | yes | yes | 4 | 3 | matches process names, not real windows | P2 |
| Search | search pill UI only | MISSING (UI shell only) | no | no | 3 | 0 | no index, no results, not clickable | P2 |
| File Explorer | Dolphin fork (planned) | MISSING | no | no | — | — | nothing written | P1 |
| Settings | Bedrock Settings (planned) | MISSING | no | no | — | — | nothing written | P2 |
| Context menus | — | MISSING | no | no | — | — | Windows 11 rounded menus not started | P2 |
| Notifications | — | MISSING | no | no | — | — | no notification daemon | P2 |
| Quick settings | — | MISSING | no | no | — | — | needs NetworkManager/PipeWire/UPower backends | P2 |
| Window snapping / snap layouts | KWin rules (planned) | MISSING | no | no | — | — | never run on a compositor | P2 |
| Alt+Tab / Task view | KWin (planned) | MISSING | no | no | — | — | — | P3 |
| Virtual desktops | KWin (planned) | MISSING | no | no | — | — | — | P3 |
| Run dialog (Win+R) | — | MISSING | no | no | — | — | — | P3 |
| Clipboard history (Win+V) | Klipper (planned) | MISSING | no | no | — | — | — | P4 |
| Screenshots (Win+Shift+S) | Spectacle (planned) | MISSING | no | no | — | — | — | P3 |
| File associations | XDG mime (planned) | MISSING | no | no | — | — | — | P3 |
| Terminal | Konsole (reuse, planned) | MISSING | no | no | — | — | not integrated | P3 |
| PowerShell | PowerShell 7, optional profile | MISSING | no | no | — | — | Windows-only modules will never work | P5 |
| Task Manager | `bedrock-sysprobe` backend | BACKEND ONLY | CLI only | yes (unit) | — | — | no GUI | P3 |
| Device Manager | `bedrock-hwinfo` backend | BACKEND ONLY | CLI only | yes (unit) | — | — | no GUI | P3 |
| Update workflow | bootc atomic + rollback (planned) | MISSING | no | no | — | — | base decision reopened | P2 |
| Recovery workflow | btrfs snapshot / previous deployment | MISSING | no | no | — | — | contract only | P2 |
| Application installation | Flatpak + Store (planned) | MISSING | no | no | — | — | — | P2 |
| Networking / audio / Bluetooth | NM / PipeWire / BlueZ (chosen) | MISSING | no | no | — | — | never run | P1 |
| Multi-monitor | KWin | MISSING | no | no | — | — | never run | P2 |
| Accessibility | Orca + Qt a11y (planned) | MISSING | no | no | — | — | not started | P2 |
| Registry | config files | NOT APPLICABLE | — | — | — | — | by design | — |
| Windows Defender | SELinux/firewalld/sandboxing | NOT APPLICABLE (alternative) | — | — | — | — | different security model | — |

**Summary: 0 COMPLETE, 3 PARTIAL, 3 PROTOTYPE, 2 BACKEND ONLY, 21 MISSING.** That is the honest state
of parity today.
