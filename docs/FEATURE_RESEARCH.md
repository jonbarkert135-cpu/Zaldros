# Feature research — what to take from other systems

Rule: adopt only what measurably improves Bedrock, and never copy blindly (spec PART 1 §9–10).
Each row says what to take **and** what it costs us.

## Distributions

| Source | Worth taking | Why | Cost |
| --- | --- | --- | --- |
| **Linux Mint** | Timeshift-style snapshot restore surfaced in the UI; Driver Manager; Update Manager that ranks updates by risk | Mint's core insight is that ordinary users need *recovery and drivers* to be one obvious button, which matches our Windows-user audience exactly | maintaining a GUI for each |
| **Ubuntu** | HWE kernel model (stable base, fresh kernel option); packaged and signed NVIDIA drivers; OEM hardware certification lists | Directly solves "must run on all devices, weak and modern" without a rolling base | ties us to the Debian family |
| **Debian** | Long-lived stable base; debconf-style non-interactive configuration; superb architecture support | Best proven base for weak/old hardware | conservative kernel; needs backports |
| **Arch** | The Wiki as a documentation standard; `mkinitcpio` clarity; minimal install as a debugging tool | Documentation quality is a feature; rolling is not what we want, its *docs* are | none, if we only borrow ideas |
| **Fedora** | bootc/ostree atomic updates with rollback; Wayland-first defaults; SELinux enforcing by default | The strongest update/recovery story available today, which our spec demands | image model conflicts with "install anything system-wide" |
| **openSUSE** | Snapper + grub-btrfs: boot straight into a pre-update snapshot | Exactly the rollback mechanism we need if we go Debian-family | btrfs-only |
| **Pop!_OS** | Hybrid-graphics switching that actually works; separate NVIDIA ISO | Removes our single most common expected failure | two ISOs to build and test |

## Desktops

| Source | Worth taking | Why | Cost |
| --- | --- | --- | --- |
| **KDE Plasma** | KWin (mature Wayland compositor, scripting, window rules), layer-shell panels, KWin effects, Dolphin, Spectacle, Konsole | Gives us 80 % of the desktop for free; Windows-like paradigms already fit Plasma better than GNOME | theme drift on every KDE release |
| **GNOME** | Excellent accessibility stack (Orca), Boxes-style guided flows, GNOME Software's app metadata (AppStream) | Accessibility and app metadata are gaps we have | GNOME's UX paradigms are the opposite of Windows-like |
| **Cinnamon** | Proof that a Windows-style shell can be maintained long term by a small team | Validates our approach and its cost | it also shows how much work a shell is |
| **Zorin / Wubuntu-style projects** | What *not* to do: a theme on top of GNOME/Plasma that breaks on update and never gets behaviour right | Confirms our decision to build the shell properly rather than ship a theme | — |
| **XFCE / LXQt** | Genuinely low resource desktops — the reference point for our Legacy profile benchmarks | Gives an honest baseline to compare against | — |

## Techniques worth adopting now

1. **zram + zstd** swap for low-RAM machines (Fedora default, measurable win on weak PCs).
2. **`systemd-analyze blame` in CI** so boot regressions are caught automatically — already wired into
   `bedrock-bench`.
3. **AppStream metadata** for the Store instead of a hand-maintained app list.
4. **grub-btrfs + snapper** as the rollback path if the base becomes Debian-family.
5. **Weblate** for translations, as most upstream desktop projects use.
6. **`fwupd`** for firmware updates — Windows users expect firmware updates to just happen.
7. **Power profiles daemon** for the Desktop/Performance/Legacy profiles instead of custom tuning.

## Explicitly rejected

- Copying Windows artwork, icons or sounds (legal boundary, spec PART 1 §2).
- Shipping a Plasma theme and calling it a distribution.
- Telemetry of any kind, even "anonymous" (spec PART 4 §14).
- Chasing an idle-RAM headline by disabling services users need (spec PART 5 §2).
