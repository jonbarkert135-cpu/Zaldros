# ADR-0001 — Base distribution: Fedora (bootc)

Status: accepted (Phase 0), re-verified before Phase 2.
Context: spec PART 1 §4 requires an evidence-based base choice; the product needs a Windows-like
update-and-rollback experience, reproducible builds and fresh hardware support.
Decision: Fedora bootable-container base; `/usr` read-only; atomic A/B updates; SELinux enforcing.
Alternatives: Debian stable (largest archive, no atomic rollback), Arch (rolling, poor release QA),
Ubuntu (snapd conflicts with minimalism), Alpine/LFS (desktop/hardware coverage cost).
Consequences: OS is defined by a Containerfile and built in CI; runtime package installation is
discouraged; `.deb`-only software needs Flatpak or distrobox. Fallback documented: Debian + custom A/B.
