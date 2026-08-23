# ADR-0004 — Filesystem: btrfs + zstd, zram swap

Status: accepted (provisional — to be confirmed by measurement in Phase 1).
Context: image-based OS with rollback, desktop workload, wide range of hardware including HDDs.
Decision: btrfs with subvolumes and zstd:1 compression for `/` and `/home`, zram swap sized to
50 % of RAM, `/usr` read-only via ostree.
Alternatives: ext4 (fast, no snapshots/compression), xfs (no useful snapshot story for desktop).
Consequences: snapshots and compression help the Legacy profile on small/slow disks; btrfs CPU cost
must be measured against ext4 before Phase 2 sign-off.
