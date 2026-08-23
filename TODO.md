# TODO

Priority follows the owner's order: bootable system → real desktop → shell → taskbar/Start →
Explorer → Settings → hardware → installer/updates → compatibility → performance → visual fidelity.

## Blocking everything
- [ ] Confirm the GitHub Actions `image` job builds a container image (first real build evidence)
- [ ] Get a build host with `/dev/kvm` (CI cannot boot a VM comfortably) — or the owner's machine
- [ ] Settle the base distribution with the test in `docs/research/03-base-distribution-reopened.md`

## Real desktop (next slice)
- [ ] Turn the taskbar into a real Wayland **layer-shell** panel on KWin (not a window)
- [x] Parse `.desktop` files; pins now cross-checked against the real application database
- [x] Launch applications from Start and from the taskbar
- [ ] Track real windows from the compositor; group them in the taskbar
- [ ] Wire quick-settings toggles to NetworkManager / BlueZ / PipeWire / UPower
- [ ] Vendor Fluent UI System Icons (MIT) and Selawik (OFL) once the build host has network
- [ ] Window management: Alt+Tab, snap layouts, minimise/maximise/close on real windows
- [ ] Autostart the shell in a session (login → desktop)
- [ ] Search: applications first, then settings, then files
- [ ] Right-click context menus (Windows 11 rounded style)
- [ ] Notifications + quick settings backed by real NetworkManager / PipeWire / UPower

## After the desktop stands up
- [ ] Explorer (Dolphin fork) — first real system application
- [ ] Settings (display, network, sound, accounts)
- [ ] Installer, then recovery/rollback tested by deliberately breaking a VM
- [ ] First hardware evidence records; first performance baselines vs Ubuntu/Mint/Fedora/Debian
- [ ] Accessibility pass (Orca, keyboard-only, high contrast)
- [ ] Paste the verbatim GPL-3.0 text into `LICENSE` (no network in the build sandbox)
