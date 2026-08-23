# Third-party components

Required by spec PART 1 §11. Every third-party component that ships in a Zaldros OS image must be
listed here with project, version, source, license, our modifications and redistribution requirements.

**No proprietary Microsoft binaries, fonts, icons, cursors or wallpapers may ever be added to this
repository or to a Zaldros image.** Segoe UI, the Windows icon set and Windows wallpapers are
proprietary; Zaldros ships open substitutes (see below) and may optionally import assets from a
Windows installation the user themselves licenses, at their explicit request, at runtime.

| Project | Version | Source | License | Modifications | Redistribution requirements |
| --- | --- | --- | --- | --- | --- |
| _(none yet — Phase 0)_ | | | | | |

## Planned components (to be recorded here when first included in an image)

| Project | Expected role | License |
| --- | --- | --- |
| Linux kernel (Fedora build) | kernel | GPL-2.0 |
| systemd | init & service management | LGPL-2.1+ |
| bootc / libostree | image-based atomic updates | Apache-2.0 / LGPL-2.0+ |
| KWin (KDE Plasma 6) | Wayland compositor | GPL-2.0+ |
| Qt 6 | shell & application toolkit | LGPL-3.0 (dynamic linking) |
| PipeWire / WirePlumber | audio & video | MIT |
| NetworkManager | networking | GPL-2.0+ |
| BlueZ | Bluetooth | GPL-2.0+ |
| Flatpak | user application format | LGPL-2.1+ |
| Wine / Proton | Windows compatibility (optional component) | LGPL-2.1+ |
| Inter / Selawik | open substitutes for Segoe UI | OFL-1.1 / MIT |

Zaldros OS is an independent Linux project. It is not affiliated with, endorsed by, or distributed
by Microsoft. Windows and Windows 11 are trademarks of Microsoft Corporation.
