# Visual third-party components — research and licence audit

Purpose: before any external code, artwork or font enters the visual layer, its licence must be
checked and recorded here (spec PART 1 §11, VISUAL FOUNDATION RECOVERY §2).
Researched 2026-08-23 via public repositories and vendor documentation. **"Used in Zaldros" = "no"
everywhere below means nothing has been vendored yet** — this table is the decision record, not a
claim that the code is already in the tree.

## 1. Candidate components

| Component | Source | Licence | Can modify? | Can redistribute? | Attribution required? | Used in Zaldros? |
| --- | --- | --- | --- | --- | --- | --- |
| **Fluent UI System Icons** | github.com/microsoft/fluentui-system-icons | **MIT** (Microsoft) | yes | yes | yes — keep MIT notice | **Chosen** for system/tray iconography; not yet vendored (no network in build sandbox) |
| **Selawik** | github.com/microsoft/Selawik | **SIL OFL 1.1** (Microsoft) | yes (rename if modified) | yes | OFL notice | **Chosen** as the UI font — Microsoft's own open replacement for Segoe UI, metric-compatible |
| **Inter** | github.com/rsms/inter | SIL OFL 1.1 | yes | yes | OFL notice | Fallback / Latin alternative |
| **Noto Sans** | Google Fonts | SIL OFL 1.1 | yes | yes | OFL notice | Fallback, needed for Cyrillic coverage breadth |
| **Papirus icon theme** | github.com/PapirusDevelopmentTeam/papirus-icon-theme | GPL-3.0 | yes | yes | yes | Candidate for application icons (GPL-3.0 matches our licence) |
| **Win11OS-kde** (Plasma theme) | github.com/yeyushengfan258/Win11OS-kde | GPL-3.0 | yes | yes | yes | **Rejected as a base** — see §3 |
| **Win11-icon-theme** | github.com/yeyushengfan258/Win11-icon-theme | GPL-3.0 | yes | yes | yes | **Rejected** — licence is GPL but the artwork's provenance vs Microsoft's icons is unverified |
| **Menu 11 / OnzeMenuKDE** | github.com/adhec/OnzeMenuKDE | GPL-2.0+ | yes | yes | yes | Studied as reference; GPL-2.0+ is compatible with GPL-3.0-or-later |
| **menu-11-next** (Plasma 6 fork) | github.com/justtails/menu-11-next | GPL-2.0+ | yes | yes | yes | Studied — closest working Windows 11 Start for Plasma 6 |
| **Menu-11-Enhanced** | github.com/kurojs/Menu-11-Enhanced | GPL-2.0+ | yes | yes | yes | Studied — grid launcher behaviour |
| **plasma-applet-tiledmenu** | github.com/Zren/plasma-applet-tiledmenu | GPL-2.0+ | yes | yes | yes | Studied — Windows 10 tile behaviour |
| **AnduinOS** | github.com/Anduin2017/AnduinOS | GPL-3.0 | yes | yes | yes | Behavioural reference (GNOME-based, so not a code base for us) |
| **KDE Plasma / KWin / Breeze** | invent.kde.org | GPL-2.0+ / LGPL | yes | yes | yes | **Planned platform** (ADR-0002/0003) |
| **Zorin OS desktop** | zorin.com | Mixed; Zorin-specific artwork is **not** freely redistributable | no | no | — | Reference only, never copied |
| **Winux / Wubuntu / Linuxfx** | winux.is | **Proprietary**, paid PowerTools | no | no | — | **Forbidden** |
| Microsoft Windows artwork, Segoe UI, Windows logo, Copilot mark | — | Proprietary | no | no | — | **Forbidden** (PART 1 §2) |

## 2. The two findings that matter

Microsoft itself publishes an open icon set (**Fluent UI System Icons, MIT**) and an open Segoe UI
replacement (**Selawik, OFL**). Together these give a legally clean Windows-native *look* for
typography and system iconography without touching a single proprietary asset. This is a better
answer than any third-party "Win11 theme" pack, and it is the route Zaldros takes.

## 3. Why we do not build on an existing Windows-11 KDE theme

The brief says: do not reinvent what open source already does well. We evaluated that honestly.

- Those projects (Win11OS-kde, menu-11-next, Menu-11-Enhanced) are **Plasma theming plus a launcher
  plasmoid**. They change how Plasma looks; they do not change how it behaves. Every review of the
  distributions built that way lands on the same verdict — looks close, behaves like KDE.
- Their artwork provenance is unverified. Win11-icon-theme ships icons visually indistinguishable
  from Microsoft's, under a GPL notice that cannot itself grant rights to artwork the packager did
  not create. Shipping them would put the exact legal risk on us that PART 1 §2 forbids.
- We *are* reusing the heavy machinery: KWin, Plasma's Wayland stack, Dolphin, Konsole, Spectacle.
  That is where reuse pays. The shell — taskbar, Start, tray, quick settings — is the part that must
  be genuinely ours because that is precisely the part nobody has done properly.

What we do take from them: layout measurements, interaction patterns, and the plasmoid source as a
behavioural reference (their GPL-2.0+ terms are compatible with our GPL-3.0-or-later).

## 4. Obligations if these are vendored

| Licence | What we must do |
| --- | --- |
| MIT (Fluent icons) | Ship the MIT text and copyright notice with the icons |
| SIL OFL 1.1 (Selawik, Inter, Noto) | Ship the OFL text; do not sell the fonts alone; rename if modified |
| GPL-2.0+ / GPL-3.0 (Plasma, Papirus, launchers) | Ship source and licence; our derived code stays GPL |

Every entry that moves to "used" must also be added to `THIRD_PARTY_LICENSES.md` with its version.
