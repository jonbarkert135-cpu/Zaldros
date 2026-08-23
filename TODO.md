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
- [x] Vendor Fluent UI System Icons (MIT) and Selawik (OFL) — done, in use
- [ ] Vendor Fluent-icon-theme (GPL-3) for app/mime icons and its cursor theme
- [ ] Ship Win11-gtk-theme (GPL-3) so GTK applications match the shell
- [ ] Build the ISO the AnduinOS way (debootstrap + squashfs + xorriso) — no container runtime needed
- [ ] Window management: Alt+Tab, snap layouts, minimise/maximise/close on real windows
- [ ] Autostart the shell in a session (login → desktop)
- [ ] Search: applications first, then settings, then files
- [ ] Right-click context menus (Windows 11 rounded style)
- [ ] Notifications + quick settings backed by real NetworkManager / PipeWire / UPower

## After the desktop stands up
- [ ] Explorer (Dolphin fork) — first real system application
- [ ] Settings (display, network, sound, accounts)
- [ ] Installer, then recovery/rollback tested by deliberately breaking a VM
- [ ] **Re-earn what the bootc base gave us** (ADR-0009): atomic updates, rollback, read-only `/usr`,
      on-disk recovery entry. Until these exist, do not claim any of them anywhere in the docs.
- [ ] Pin package versions in `build/iso/build-iso.sh` — builds are repeatable, not reproducible
- [ ] Mark `build/Containerfile.*` dead or delete them; they belong to the superseded bootc base
- [ ] First hardware evidence records; first performance baselines vs Ubuntu/Mint/Fedora/Debian
- [ ] Accessibility pass (Orca, keyboard-only, high contrast)
- [ ] Paste the verbatim GPL-3.0 text into `LICENSE` (no network in the build sandbox)
