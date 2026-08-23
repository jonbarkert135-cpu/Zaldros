# ADR-0001 — Base distribution: Fedora (bootc)

Status: **SUPERSEDED by ADR-0009 (proposed)** — the base moved to Ubuntu 26.04 LTS on 2026-08-23.
Kept as the record of the bootc option and of the properties (atomic updates, rollback, immutability,
SELinux) that the move gives up; ADR-0009 lists what replaces each of them.
Context: spec PART 1 §4 requires an evidence-based base choice; the product needs a Windows-like
update-and-rollback experience, reproducible builds and fresh hardware support.
Decision: Fedora bootable-container base; `/usr` read-only; atomic A/B updates; SELinux enforcing.
Alternatives: Debian stable (largest archive, no atomic rollback), Arch (rolling, poor release QA),
Ubuntu (snapd conflicts with minimalism), Alpine/LFS (desktop/hardware coverage cost).
Consequences: OS is defined by a Containerfile and built in CI; runtime package installation is
discouraged; `.deb`-only software needs Flatpak or distrobox. Fallback documented: Debian + custom A/B.


## Amendment 2026-08-23 — the LTS must be 26.04, not 24.04
Ubuntu 24.04 LTS ships Plasma 5.27 / Qt 5; KWin 6 and layer-shell-qt 6 first appear in Ubuntu 26.04
LTS (`resolute`): kwin-wayland 4:6.6.4, layer-shell-qt 6.6.4, Qt 6.10. Since ADR-0002/0003 depend on
KWin 6 and Qt 6, the base suite is **`resolute` (26.04 LTS)**. [archive.ubuntu.com indices, 2026-08-23]
