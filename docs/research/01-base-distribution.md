# Research 01 — Base distribution selection

Requirement: spec PART 1 §4 — compare candidates on evidence, do not default to Ubuntu/Debian/Arch/Fedora.

## Candidates evaluated

| Candidate | Model | Kernel freshness | Packages | Update model | Buildability of a custom OS |
|---|---|---|---|---|---|
| Debian stable (13 trixie) | traditional, apt | conservative (backports available) | ~150k, largest archive | in-place apt | very good: live-build, debootstrap, decades of derivative distros |
| Ubuntu LTS | traditional, apt + snap | good HWE kernels | large | in-place + snap | good, but Canonical-specific layers (snapd) conflict with minimalism |
| Arch | rolling, pacman | newest | ~15k official + AUR | rolling | good (archiso), but rolling base is hostile to a shipped product's QA |
| Fedora Workstation | traditional, dnf | very fresh, upstream-first | ~70k | in-place dnf | good (kickstart/livemedia) |
| **Fedora bootc / atomic (CNCF)** | image-based OCI | very fresh | Fedora archive + layering | **atomic A/B image + instant rollback** | excellent: OS is a Containerfile; reproducible, CI-buildable |
| Alpine / LFS / Gentoo | minimal / source | n/a | small / source | n/a | rejected: hardware + desktop package coverage cost outweighs gains |

## Evidence

- `bootc` is a CNCF Sandbox project; official bootable base images exist for Fedora, CentOS Stream,
  AlmaLinux and RHEL. The OS is built with ordinary container tooling (Containerfile + podman),
  `/usr` is read-only, updates are downloaded in the background and applied atomically on reboot with
  the previous image preserved for rollback. (LWN "Bootc for workstation use"; Fedora Magazine
  "Building your own Atomic (bootc) Desktop"; blogs.oracle.com/linux/bootc-read-only-root-filesystem)
- Shipping distributions already use this exact path in production (Bluefin, Universal Blue, BlueBuild),
  which proves the "custom desktop OS as an image" workflow is viable, not experimental.
- Debian's advantage is archive size and stability; its disadvantage for this project is that
  in-place `apt` upgrades give no atomic rollback, and a Windows-like "update and restart, roll back if
  broken" experience then has to be built from scratch.
- Arch's rolling base makes reproducible, testable releases substantially harder — directly conflicts
  with spec PART 1 §12 (reproducible builds, versioned releases, known-good state).
- bootc on Debian exists only as unofficial/experimental images (per BlueBuild FAQ, 2026-06), so
  "Debian + atomic" is not currently a supported combination.

## Decision

**Primary base: Fedora (bootc / bootable-container flavour), kernel from Fedora, SELinux enforcing.**

Rationale, mapped to the spec's evaluation criteria:

- *Update system* (a required Windows-like workflow): atomic update + guaranteed rollback out of the box.
- *Reproducibility / buildability* (§12): the whole OS is a Containerfile built in CI; every build is
  versioned and byte-addressable; "never destroy the last known-good version" is enforced by the design.
- *Kernel freshness / hardware support*: Fedora tracks upstream closely — important for modern laptops,
  Wayland, HDR and GPU drivers.
- *Security* (§ security strategy): SELinux enforcing + read-only `/usr` gives a stronger default than
  AppArmor on a mutable root.
- *Performance*: image-based systems remove per-machine package-manager work at update time; boot
  performance is governed by our service map, not by the base.

**Fallback (documented, re-evaluated at the end of Phase 1): Debian stable + custom A/B image tooling**,
if Fedora's package or licensing constraints (e.g. codec/driver availability for the target audience)
prove blocking.

**Risk accepted:** third-party app expectations are Debian-shaped (many vendors ship `.deb` only).
Mitigation: Flatpak as the primary user-application format (vendor-neutral), plus a documented
`distrobox`/container path for `.deb`-only tools.

Status: **accepted for Phase 1**, to be re-verified with a measured VM comparison (boot time, idle RAM,
update duration) before Phase 2 — see `docs/state/PROJECT_STATE.md`.
