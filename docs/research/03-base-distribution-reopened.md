# Research addendum — base distribution reopened (Fedora bootc vs Debian family)

Trigger: owner feedback 2026-08-23 — *"за основу ты взял какое-то непопулярное… думал ты возьмёшь
Arch или Debian"*, together with the priority *maximum device coverage: very weak PCs, weak PCs and
powerful PCs alike*.

## 1. Clearing up one thing first

"Fedora bootc" is **not** an obscure distribution. It is Fedora — a top-tier distribution, upstream of
RHEL — packaged as a container image (`bootc`), which is the same technology behind Fedora Silverblue.
The unusual part is the *packaging format*, not the base. So the concern is fair but slightly
misdirected: the risk is not obscurity, it is that few of our users will have seen an image-based OS.

## 2. What actually matters for the stated goal

The goal "runs well on very weak, weak and powerful machines" splits into two different needs that pull
in opposite directions:

| Need | Favours | Why |
| --- | --- | --- |
| New hardware (recent laptops, new GPUs, Wi-Fi) | Fedora / Arch | fresh kernel and Mesa; drivers land months earlier |
| Old and weak hardware, long-term stability | Debian / Ubuntu LTS | mature drivers, low churn, very long support windows, HWE kernels give the fresh option too |
| Proprietary NVIDIA convenience | Ubuntu | packaged and signed in-archive; Fedora needs RPM Fusion |
| Familiarity, documentation, community answers in Russian | Ubuntu / Debian / Mint | by far the largest body of tutorials and forum answers |
| Third-party `.deb` software (Chrome, Steam, VS Code, Yandex) | Debian family | vendors ship `.deb` first |
| Atomic updates + guaranteed rollback | Fedora bootc | built in; on Debian family we must build it ourselves |

Ubuntu LTS with the HWE kernel closes most of the "new hardware" gap, which was the strongest argument
for Fedora. Mint and Pop!_OS both prove the Debian-family route for exactly this kind of product.

## 3. Recommendation

**Reopen ADR-0001 and default to an Ubuntu LTS base (24.04 LTS + HWE kernel)** for v1, unless the
Phase 1 build test contradicts it. Reasons, in the spec's own priority order (PART 5 §16):
hardware compatibility and usability outrank architectural elegance, and the Debian family wins on
device coverage, driver convenience, third-party software and documentation.

Cost of the switch, stated honestly: we lose free atomic updates and rollback. Those are a hard
requirement (PART 4 §15–16, `RECOVERY.md`), so they must be rebuilt as **btrfs snapshots + a boot menu
entry for the previous snapshot** — a well-trodden path (Snapper/Timeshift + grub-btrfs) but real work
in Phase 10/11.

## 4. The deciding test (Phase 1, not opinion)

Build both minimal images and boot each on the reference machine, then record with our own tools:

1. `bedrock-hwinfo` — does every device resolve (Wi-Fi, GPU, audio, touchpad, suspend)?
2. `bedrock-bench collect` — boot stages and used RAM on the weakest available machine.
3. Time and disk cost of one full update, and a deliberate rollback after a broken update.

Whichever base passes on the weakest machine *and* survives a broken-update rollback becomes final.
Both candidates are recorded until then; the tooling written so far (`sysprobe`, `hwinfo`, `compat`,
`bench`) is base-agnostic and needs no changes either way.

**Blocker for this test: it needs a real machine or CI. That is the same blocker as everything else.**
