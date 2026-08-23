# Feature research — what to take from other systems

Rule: adopt only what measurably improves Zaldros, and never copy blindly (spec PART 1 §9–10).
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

## The closest existing competitor: Linuxfx → Wubuntu → Winux

This project already exists in the market and must be studied openly, so this section names it directly
(an earlier draft only alluded to it as "Wubuntu-style projects" — that was an omission).

**What it is.** A Brazilian distribution by Rafael Rachid, released in 2007 as Linuxfx (also branded
Windowsfx), rebranded to **Wubuntu**, then to **Winux** in 2025. Current builds are Kubuntu/Ubuntu
24.04 LTS + KDE Plasma with a Windows 11 theme, plus Wine, an Android VM and a "PowerTools" bundle.
Reception is genuinely split: Windows Central and Tom's Hardware praise it as the friendliest
on-ramp for Windows refugees; The Register, XDA and MakeUseOf recommend avoiding it.

**Why it is not our answer, on our own spec's terms:**

| Their approach | Our rule |
| --- | --- |
| Ships Windows 11 look-alike icon/theme packs, Windows boot logo, a Copilot icon; The Register found no attribution for the artwork's origin | PART 1 §2 — no protected Microsoft assets without checked licensing |
| Uses the name "Windows Ubuntu"/Winux; trademark concerns raised repeatedly, including for the Ubuntu name | We chose our name specifically to avoid a collision (ADR-0005) |
| **Proprietary licence**, $35 "PowerTools", nag pop-ups pushing the paid version, preinstalled proprietary apps | GPL-3.0-or-later, no upsells, no nagging |
| 2022 activation database leak (IPs, e-mail addresses, licence keys); the reporter was mocked rather than the bug fixed | PART 4 §14 — no telemetry, no activation servers, and security reports get fixed |
| Windows compatibility = Wine preinstalled, marketed as ".exe support" | PART 4 — every application must be classified with tested evidence, never "we support .exe" |
| Depth is theming: behaviour is still KDE underneath | We build a real shell, because a theme cannot deliver Windows behaviour |

**What is genuinely worth learning from it:**
1. The demand is real and large — its coverage exists because Windows 10's end of life pushed people to look.
2. Ubuntu LTS + KDE Plasma is a *proven* base for exactly this goal, which supports the direction in
   `docs/research/03-base-distribution-reopened.md`.
3. Reviewers consistently praise one thing above all: **a simple installer and a familiar first boot**.
4. Its recurring criticisms are the failure modes we must design against: nagware, unclear licensing,
   copied artwork, opaque security practice, superficial compatibility promises.
5. Not requiring TPM/Secure Boot is a headline selling point for people with older PCs.

**Related, cleaner references:** Zorin OS (commercial, legally careful) and AnduinOS (Ubuntu-based,
Windows-like, built by a Microsoft engineer) are better behavioural references than Winux.

Sources: The Register 2024-12-05; Tom's Hardware 2025-08-14; XDA 2025-09-17; MakeUseOf 2025-09-25;
Windows Central 2025-09-07; TechRadar 2021-01-24; Wikipedia "Winux". [web, 2026-08-23]

## Techniques worth adopting now

1. **zram + zstd** swap for low-RAM machines (Fedora default, measurable win on weak PCs).
2. **`systemd-analyze blame` in CI** so boot regressions are caught automatically — already wired into
   `zaldros-bench`.
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
