# Installing Zaldros OS

**There is no installable image yet.** This file describes the intended installation contract so the
installer (Phase 10) can be built against it; it will be replaced with real instructions once an image
boots.

Planned: UEFI boot from a written USB image → live environment → **Zaldros Setup** → language,
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

## Trying the live ISO on real hardware, and sending the evidence back

There is no installer yet, but there is a live ISO, and the only thing nobody has done with it is
boot it on a physical machine. That takes three steps and one command.

1. **Get the ISO.** Either download the `iso-full` artifact from a green `iso` workflow run
   (≈2.83 GiB, GitHub → Actions → the run → Artifacts), or build it yourself as `BUILD.md`
   describes. The artifact is a zip; the `.iso` is inside it.
2. **Write it to a USB stick.** On Windows: Rufus, *DD image* mode (not ISO mode), or Ventoy —
   ≥8 GB, the stick is erased. Then in the firmware: **Secure Boot off** (the image's GRUB is not
   signed by Microsoft's shim), boot from the stick. On an NVIDIA Optimus laptop, if the screen
   stays black, boot GRUB's entry with `nomodeset` before filing anything.
3. **Collect the evidence, working or not.** In the live session:

   ```bash
   zaldros-collect-logs            # inside the image; ./tools/collect-logs.sh from a checkout
   ```

   It prints the path of one `.tar.gz` — the boot journal, `dmesg`, failed units and pending jobs,
   `systemd-analyze`, the session log, what the shell's backend saw on this machine (every tray
   reading with its source and its reason for being empty), CPU/PCI/USB/disk/network/audio/input
   inventory, Secure Boot state, and a screenshot if a screenshot tool answered. It never collects
   Wi-Fi keys, the password database or anything from home, so the archive is safe to hand over.
   Copy it to the stick (or the Windows partition) and send it.

If the desktop never appears, the archive is still the answer: `14-systemd-failed.txt` and
`20-session-journal.log` say which unit died, and `35-backend-status.json` says which service the
shell could not reach.
