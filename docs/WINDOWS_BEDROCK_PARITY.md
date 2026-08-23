# Windows 11 ↔ Bedrock OS parity

(Requested as `WINDOWS_RAVEN_PARITY.md`; renamed to match the official project name — see `docs/NAMING.md`.)

Status values: COMPLETE / PARTIAL / PROTOTYPE / BACKEND ONLY / MISSING / NOT APPLICABLE.
**Working?** and **Tested?** are separate columns on purpose: something can render and still be untested,
and something can be tested and still be useless to a user. Similarity is rated 0–5, and is only filled
in where a real frame exists to compare against the reference screenshot.

| Windows feature | Bedrock implementation | Status | Working? | Tested? | Visual | Behaviour | Known limitations | Priority |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Desktop + wallpaper | QML desktop with icons, dark/light themes | PROTOTYPE | yes (rendered) | yes (render tests) | 3.5 | 2 | icons are not interactive; no wallpaper engine | P2 |
| Taskbar | Bedrock Taskbar (QML), Windows 11 metrics | PROTOTYPE | yes (rendered) | yes | 4.0 | 3 | window, not a layer-shell panel; no real window list | P1 |
| Start menu | Bedrock Start, 640×726, pins + all apps | PARTIAL | yes — launches real apps | yes | 4.0 | 3 | no search results, Recommended empty by design | P1 |
| Taskbar clock | real locale-formatted system clock | PARTIAL | yes | yes | 4 | 4 | no calendar flyout | P3 |
| System tray | tray with real presence detection | PARTIAL | yes | yes | 3.7 | 2 | no per-icon backends, overflow is static | P2 |
| Launching applications | real .desktop parsing + launch | PARTIAL | yes | yes (unit) | — | 3 | no window tracking after launch | P1 |
| Running-app indicator | underline driven by real `/proc` process table | PARTIAL | yes | yes | 4 | 3 | matches process names, not real windows | P2 |
| Search | search field in taskbar and Start | MISSING (UI only) | no | render only | 3.0 | 0 | no index, no results | P2 |
| File Explorer | Dolphin fork (planned) | MISSING | no | no | — | — | nothing written | P1 |
| Settings | Bedrock Settings (planned) | MISSING | no | no | — | — | nothing written | P2 |
| Context menus | Bedrock ContextMenu (QML) | PROTOTYPE | renders | yes | 3.8 | 2 | items perform no actions | P2 |
| Notifications | — | MISSING | no | no | — | — | no notification daemon | P2 |
| Quick settings | Bedrock quick settings flyout | PARTIAL | yes — real readouts | yes | 3.7 | 2 | toggles not wired; unavailable items shown as unavailable | P2 |
| Window decorations | Bedrock AppWindow design (KWin will draw) | PROTOTYPE | renders | yes | 3.7 | 2 | design only, no window management | P2 |
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

**Summary: 0 COMPLETE, 6 PARTIAL, 5 PROTOTYPE, 2 BACKEND ONLY, 19 MISSING.**
Visual scores live in `docs/VISUAL_SCORE.md`; a score is a design metric, never proof of function.
