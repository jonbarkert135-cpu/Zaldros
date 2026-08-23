# Installing Bedrock OS

**There is no installable image yet.** This file describes the intended installation contract so the
installer (Phase 10) can be built against it; it will be replaced with real instructions once an image
boots.

Planned: UEFI boot from a written USB image → live environment → **Bedrock Setup** → language,
keyboard, timezone, disk selection, optional LUKS2 encryption (**off by default**, as in Ubuntu, Mint and Debian), user account, installation profile
(Desktop / Performance / Legacy) → install → reboot → optional first-run wizard.

Safety contract (spec PART 4 §20, PART 5 §20): every destructive disk operation shows exactly which
device and which data will be erased and requires explicit confirmation. Nothing is written to disk
before that confirmation.

## Disk encryption contract (ADR-0005 §4)

Off by default. The installer offers it as one clear checkbox stating both the benefit (protects a lost
or stolen machine) and the cost (a password at every boot; **data is unrecoverable without it**). If
enabled, the recovery-key screen must be shown and confirmed before installation continues.

## Language

The published ISO defaults to Russian; English is fully supported, and the installer offers the tier-2
language set. A Latin keyboard layout is always configured alongside a non-Latin one, switchable with
Alt+Shift / Win+Space.
