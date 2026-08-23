# Specification audit — PARTS 1–5 combined

Required by PART 5 (preamble and §25.2/§25.3): review the complete specification and identify
conflicts, missing requirements, technical risks and architectural contradictions — and do not
implement blindly where research shows a better approach.

Status: all five parts received (2026-08-23). Nothing below is a complaint about the spec; each item
is a decision point that would otherwise be resolved silently and wrongly during implementation.

---

## A. Contradictions between parts

**A1. Performance profiles vs. "do not remove drivers" — RESOLVED.**
PART 1 §8 asks for a "Legacy"/"Performance" profile with minimal background overhead; PART 4 §6 says
drivers must never be removed for performance, and PART 5 §2 forbids disabling essential services to
win a RAM number. *Resolution:* profiles are **runtime-only** — they change service activation policy,
compositor effects, polling intervals and power-profile, never the set of installed kernel modules,
firmware or security services. Recorded in `docs/architecture/PERFORMANCE.md` and enforced by the
benchmark harness metadata (a profile change that alters the driver set fails review).

**A2. "Windows-like UX" vs. "never sacrifice stability for visual similarity".**
PART 2 asks for close visual/behavioural fidelity; PART 5 §16 ranks visual similarity **7th** of eight
priorities. *Resolution:* fidelity is a target only where it does not require reimplementing a mature
component. Concretely: we reskin and extend KWin/Plasma rather than writing a compositor, and we accept
visible deviations (e.g. no acrylic blur on low-end GPUs) rather than shipping an unstable custom stack.
Every accepted deviation is recorded in the feature matrix instead of being hidden (§18).

**A3. Immutable base vs. "install anything easily".**
ADR-0001 (image-based OS, read-only `/usr`) conflicts with a Windows user's expectation of "download an
.exe/.deb and run it". *Resolution:* Flatpak/AppImage/distrobox cover the user-facing case without
touching `/usr`; the Store hides the distinction. Residual risk: an app that insists on installing
system-wide (some VPN clients, some drivers) — tracked in the risk register as R-07.

**A4. Phase numbering.** PART 5 §15 defines 15 phases; the roadmap written in Phase 0 used 6 coarse
phases. *Resolution:* the roadmap is renumbered to the spec's 0–14 (see `ROADMAP.md`); the earlier
coarse phases are kept only as groupings.

**A5. "Research first, do not implement massively" (PART 1 §9, PART 5 §25) vs. "START EXECUTION NOW"
(control prompt).** *Resolution used so far:* implement narrow, fully tested, non-throwaway tooling
that the later phases need anyway (sysprobe, hwinfo, compat, bench) while the architecture is settled
— no speculative shell or installer code before Phase 1 measurements exist.

**A6. PowerShell (PART 3 §6) vs. "no proprietary Microsoft components" (PART 1 §2).**
*Resolution:* PowerShell 7 is MIT-licensed and cross-platform, so it is legitimate — but it is an
**optional** Terminal profile, never a default shell, and Windows-only modules will not work. Stated in
the feature matrix rather than implied.

## B. Missing requirements (not covered by any part)

| # | Gap | Proposed resolution |
|---|---|---|
| B1 | **Secure Boot.** PART 5 §12 says "appropriate secure-boot strategy *if implemented*" — undecided. Without a signed shim, users must disable Secure Boot in firmware, which is a serious adoption blocker. | Decide in Phase 1: ship unsigned + documented firmware step for v0.x; pursue a shim review or a user-enrolled MOK key before v1. Needs a real decision, not a default. |
| B2 | **Localization / RU-first.** The screenshot reference is a Russian Windows 11, but no part specifies the default language, keyboard layouts or translation workflow. | Ship RU + EN as first-class from Phase 4; all shell strings translatable from the first commit (no hardcoded UI text). Awaiting your confirmation on the default locale. |
| B3 | **Accessibility.** Not mentioned anywhere: screen reader, magnifier, high contrast, keyboard-only navigation. Windows users depend on these and retrofitting is expensive. | Adopt Orca + Qt accessibility from Phase 3; every shell component must expose accessible names. |
| B4 | **Legal identity of the project**: license of Bedrock's own code, trademark, contribution terms. | Choose GPL-3.0-or-later or MIT for new code (recommend **GPL-3.0-or-later** for a distro shell) and add `CONTRIBUTING.md` + DCO. Needs your decision. |
| B5 | **Name collision** — "Bedrock Linux" is an existing unrelated project (bedrocklinux.org). | Decide before any public release: keep, or differentiate (BedrockOS / Bedrock Desktop). Asked twice; still open. |
| B6 | **Update bandwidth/offline users.** Atomic image updates are large; no part addresses metered connections or offline updates. | Delta updates via bootc/ostree static deltas + a documented offline update path; measure real update size in Phase 11. |
| B7 | **Data at rest by default.** Encryption is offered by the installer (§20) but no part states whether it is default-on. | Recommend LUKS2 default-on with a clear recovery-key screen; needs confirmation because it affects recovery UX. |
| B8 | **Crash reporting without telemetry.** §14 forbids unnecessary telemetry, §22 demands log collection for failures. | Local-only crash capture with an explicit, user-initiated "attach to report" action. Nothing leaves the machine automatically. |

## C. Technical risks worth stating plainly

- **R-1 Scope.** PARTS 1–5 describe roughly a decade of work for a funded team (a shell, ~15 system
  applications, an installer, a compatibility layer, a store, an update system). The only honest way
  forward is depth-first per phase with real acceptance gates — which is what the roadmap encodes.
- **R-2 No build host.** Nothing can be built or booted from my environment (no podman, no `/dev/kvm`).
  Until CI or a host exists, every image artefact is *written but unverified*, and no performance,
  hardware or boot claim can exist at all. This is currently the project's single largest blocker.
- **R-3 NVIDIA + Wayland** remains the most likely source of "it doesn't boot to desktop" reports.
- **R-4 Windows-fidelity expectations.** Users comparing against Windows will notice missing features
  (HDR handling, per-app DPI quirks, some hardware buttons). The feature matrix must be published, not
  hidden (§18).
- **R-5 Upstream churn.** Reskinning Plasma means every KDE release can break the theme; the visual
  regression suite (§8) is what turns that from a surprise into a failing test.

## D. Where research suggests deviating from the letter of the spec

1. **Do not build a custom compositor or shell from zero** (implied by PART 2's detail). KWin +
   layer-shell components is the only path with a realistic stability budget; a from-scratch compositor
   would violate priorities 1–4 of PART 5 §16.
2. **Do not chase a low idle-RAM headline.** An image-based OS with SELinux, PipeWire and NetworkManager
   will not beat a minimal window-manager setup on RAM, and PART 5 §2 explicitly says that is fine. Our
   published metric is *first usable interaction* and UI latency, not idle megabytes.
3. **Filesystem stays open.** btrfs is provisional; the ext4 comparison decides (PART 4 §18).

## E. Open questions for the project owner

1. B5 — project name before public release?
2. B4 — license for Bedrock's own code (recommendation: GPL-3.0-or-later)?
3. B2 — default locale RU or EN?
4. B7 — disk encryption default-on?
5. B1 — is Secure Boot support a v1 requirement?
6. Build host: can GitHub Actions be enabled, or is there a Linux machine with KVM?
7. Which physical machine is the reference laptop for baselines and the hardware matrix?
