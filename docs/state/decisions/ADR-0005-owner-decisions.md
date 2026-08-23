# ADR-0005 — Owner decisions (2026-08-23)

Status: partially superseded by ADR-0006 (name).

## 1. Name — superseded

The name decided here ("Bedrock OS") was withdrawn after the full name-availability audit
(`docs/NAME_RESEARCH.md`, 129 names checked). It collided with Bedrock Linux (an active
meta-distribution since 2009), Minecraft Bedrock Edition and BedRock Systems.
**The official name is now Zaldros OS — see ADR-0006.**

## 2. License — **GPL-3.0-or-later for Zaldros's own code**

What the references do: none of them uses a single license for everything; each ships a mixed archive
and licenses their *own* new code under a copyleft or permissive OSI license. Ubuntu's own tooling is
mostly GPL, Debian requires DFSG-free licenses, Mint's own applications (Cinnamon, mintinstall) are
GPL-2.0/GPL-3.0, Arch's own tools are GPL.

Decision:
- New Zaldros code (shell, system applications, tools): **GPL-3.0-or-later**.
- Forked components keep their upstream license (e.g. a Dolphin fork stays GPL-2.0-or-later);
  our modifications are released under the same license as the upstream component.
- No proprietary components in the base system. Everything third-party is recorded in
  `THIRD_PARTY_LICENSES.md` with project, version, source, license, modifications and redistribution
  requirements, as PART 1 §11 requires.
- `LICENSE` file added at the repo root; contribution terms in `CONTRIBUTING.md`.

## 3. Localization — **Russian and English first class, then the common set**

What the references do: install a language pack for the language chosen in the installer, ship the
rest as downloadable packs, and keep translations in a community platform (Ubuntu: Launchpad;
Debian/Arch/Mint: Weblate/Launchpad + upstream GNU gettext).

Decision:
- **Default language of the published ISO: Russian.** English is a first-class, fully supported second
  language, not a fallback.
- Tier 2 (shipped, translated as capacity allows): English, German, French, Spanish, Portuguese (BR),
  Ukrainian, Polish, Italian, Turkish, Simplified Chinese.
- Technical rule, effective from the first line of shell code: **no hardcoded user-visible strings**.
  All UI text goes through Qt's `tr()` / gettext and is extractable to `.ts`/`.po`. Retrofitting this
  later is the single most expensive localization mistake, so it is a review requirement now.
- Translation workflow: **Weblate** (used by many upstream KDE/GNOME components; free for libre
  projects), so translations are community-editable instead of hand-maintained.
- Keyboard layouts: the installer offers layout selection and always configures a Latin layout
  alongside a non-Latin one, with Alt+Shift/Win+Space switching (Windows-familiar behaviour).

## 4. Disk encryption — **off by default, offered in the installer**

What the references do — verified behaviour of the installers:
- **Ubuntu (Ubiquity/Subiquity):** unencrypted by default; LUKS is an explicit "Advanced features →
  encrypt" checkbox.
- **Linux Mint:** unencrypted by default; optional "Encrypt the new Linux Mint installation".
- **Debian (d-i):** unencrypted by default; guided "encrypted LVM" is a separate menu choice.
- **Arch:** no installer default at all; LUKS is documented and manual.

So the popular distributions agree with the owner: encryption is **opt-in, not default**. Fedora
Workstation is the outlier that pushes it more prominently, and we do not follow it here.

Decision:
- Default: **no full-disk encryption**, matching Ubuntu/Mint/Debian.
- The installer shows a clear, plain-language checkbox: what it protects (a stolen or lost machine),
  what it costs (a password at every boot, and **data is unrecoverable if the password is lost**).
- If enabled: LUKS2, and the installer *forces* the user to see and confirm the recovery key screen
  before continuing — the most common real-world failure is a user who encrypted without understanding
  recovery.
- The user's home directory permissions still protect against other local accounts regardless.
- Revisit for laptops in Phase 13 (security audit) with measured boot-time cost, not opinion.

## 5. Consequences

- `docs/NAMING.md`, `README.md` and all documents carry the final name **Zaldros OS** (ADR-0006).
- `LICENSE` (GPL-3.0-or-later) added; `CONTRIBUTING.md` license section resolved.
- Localization becomes a Phase 3 requirement, not a Phase 12 afterthought.
- `INSTALL.md` records the encryption contract above.
