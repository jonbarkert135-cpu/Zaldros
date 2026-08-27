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
- [x] Vendor Fluent UI System Icons (MIT) and PT Sans (OFL) — done, in use (Selawik dropped: no Cyrillic)
- [x] Install the Fluent cursor theme (GPL-3) — the only borrowed pack (ADR-0010)
- [ ] Draw our own Aurorae decoration theme so real app titlebars stop being Breeze
- [ ] Replace the vendored GPL-3 app/place SVGs with our own artwork (last borrowed pixels besides the cursors)
- [ ] Extend the `Zaldros` icon theme to mime and device names (currently apps/places/actions only)
- [ ] Ship Win11-gtk-theme (GPL-3) so GTK applications match the shell
- [ ] Build the ISO the AnduinOS way (debootstrap + squashfs + xorriso) — no container runtime needed
- [ ] Window management: Alt+Tab (own KWin script; the boot test now really presses Alt — awaiting
      the first verdict from a key that exists), snap layouts, minimise/maximise/close on real windows
- [ ] Autostart the shell in a session (login → desktop)
- [ ] Search: applications first, then settings, then files
- [ ] Right-click context menus (Windows 11 rounded style)
- [ ] Notifications + quick settings backed by real NetworkManager / PipeWire / UPower

## After the desktop stands up
- [ ] Explorer (Dolphin fork) — first real system application
- [ ] Settings (display, network, sound, accounts)
- [ ] **FIRST ISO BUILD PASS** — nothing else in this cycle; then first QEMU boot PASS
- [ ] Installer, then recovery/rollback tested by deliberately breaking a VM
- [ ] **Re-earn what the bootc base gave us** (ADR-0009): atomic updates, rollback, read-only `/usr`,
      on-disk recovery entry. Until these exist, do not claim any of them anywhere in the docs.
- [ ] Pin package versions in `build/iso/build-iso.sh` — builds are repeatable, not reproducible
- [ ] Mark `build/Containerfile.*` dead or delete them; they belong to the superseded bootc base
- [ ] First hardware evidence records; first performance baselines vs Ubuntu/Mint/Fedora/Debian
- [ ] Accessibility pass (Orca, keyboard-only, high contrast)
- [ ] Paste the verbatim GPL-3.0 text into `LICENSE` (no network in the build sandbox)
