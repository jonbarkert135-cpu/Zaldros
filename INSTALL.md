# Installing Bedrock Linux

**There is no installable image yet.** This file describes the intended installation contract so the
installer (Phase 10) can be built against it; it will be replaced with real instructions once an image
boots.

Planned: UEFI boot from a written USB image → live environment → **Bedrock Setup** → language,
keyboard, timezone, disk selection, optional LUKS2 encryption, user account, installation profile
(Desktop / Performance / Legacy) → install → reboot → optional first-run wizard.

Safety contract (spec PART 4 §20, PART 5 §20): every destructive disk operation shows exactly which
device and which data will be erased and requires explicit confirmation. Nothing is written to disk
before that confirmation.
