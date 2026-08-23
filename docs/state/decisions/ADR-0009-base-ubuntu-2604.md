# ADR-0009 — Base distribution moves from Fedora bootc to Ubuntu 26.04 LTS

Status: **PROPOSED — not accepted.** It becomes `accepted` only when an ISO built this way really
builds *and* boots in CI with the stage-1 and stage-2 tests passing. Until then Zaldros has no
accepted base. (spec PART 1 §15: a plan is not a result.)
Date: 2026-08-23. Supersedes ADR-0001 (Fedora bootc) if accepted.

## Why this is being written

The ISO pipeline in `build/iso/` bootstraps Ubuntu 26.04 (`resolute`) and packs it with squashfs and
xorriso. That is a different base, a different package manager and a different update model from
ADR-0001 — an architectural change, not an implementation detail, and it was drifting in unrecorded.
This ADR states it openly and prices it.

## Decision

Base = **Ubuntu 26.04 LTS (`resolute`)**, live image built from the official Ubuntu base rootfs
tarball plus apt, squashfs and xorriso.

Evidence for the suite (archive indices, 2026-08-23): Ubuntu 24.04 LTS carries Plasma 5.27 / Qt 5,
while `resolute` carries kwin-wayland 4:6.6.4, layer-shell-qt 6.6.4, plasma-workspace 4:6.6.4 and
Qt 6.10. ADR-0002 (KWin 6) and ADR-0003 (Qt 6) are unbuildable on 24.04, so within Ubuntu the LTS
must be 26.04.

Reasons to be on Ubuntu at all: the three shell architectures we are comparing are all KDE-based and
Ubuntu ships them as ordinary packages; the owner asked us to stay in line with the popular
distributions (Ubuntu / Mint / Debian / Arch) rather than sit on an exotic base; and a live ISO can
be produced on a plain GitHub runner, which is currently our only way to get real boot evidence.

## What happens to Fedora bootc

**Deferred, not deleted, and not "returned later" by default.** Precisely: the *base* decision moves
to Ubuntu; the *properties* bootc gave us are re-opened as requirements (below) and must be solved
on Ubuntu. If they cannot be solved acceptably, reverting to a bootc-style image is the documented
fallback, and ADR-0001 stays in the tree as the record of that option. Research in
`docs/research/01-base-distribution.md` and `03-base-distribution-reopened.md` remains valid input.

## What the move costs — honestly

| Property bootc gave us | Status on Ubuntu today | Replacement plan |
| --- | --- | --- |
| Atomic updates (A/B image) | **LOST** | apt is non-atomic. Candidate: btrfs snapshot before/after every apt transaction, or an A/B image scheme of our own. Not designed yet. |
| Rollback | **LOST as a boot-menu guarantee** | btrfs + snapper-style snapshots with boot entries. ADR-0004 already picks btrfs, so the substrate exists; the tooling does not. |
| Immutable / read-only `/usr` | **LOST** | Optional later (`/usr` read-only mount + overlay). Not a v1 promise. |
| Recovery environment | **PARTIAL** | The live ISO is itself a recovery environment; the on-disk recovery entry described in `RECOVERY.md` must be rebuilt on this base. |
| SELinux enforcing | **CHANGED** | Ubuntu ships AppArmor enforcing instead. Comparable in intent, different in coverage; `SECURITY.md` must stop claiming SELinux. |
| Reproducible image definition | **PARTIAL** | The Containerfile is replaced by `build/iso/build-iso.sh`; package versions are not pinned yet, so builds are repeatable but not reproducible. |

None of these are solved by this ADR. They are now open work items, tracked in `TODO.md`, and the
project must not advertise atomic updates, rollback or an immutable system model until they are.

## Consequences

- Packaging: `.deb` + apt for the system, Flatpak for applications (ADR unchanged).
- `build/Containerfile.*` become dead weight and are marked as such rather than silently kept.
- The update-center design in `docs/architecture/SYSTEM_APPS.md` loses its atomic-update assumption.
- Nothing about the shell, compositor, toolkit, filesystem or visual foundation changes.
