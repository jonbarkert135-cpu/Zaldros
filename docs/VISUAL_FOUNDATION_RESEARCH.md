# Visual foundation research — open-source Windows-like projects

Method: every project below was **cloned or fetched and inspected locally** (not judged from its
README), on 2026-08-23. Star counts were ignored; what mattered was licence, activity, technical
stack and how much of it Zaldros can legally reuse. Verdicts use five levels:
**DIRECT USE** (vendor as-is) · **ADAPT** (extract values/behaviour, reimplement) ·
**FORK** · **REFERENCE ONLY** · **WRITE OUR OWN**.

## 1. Master table

| Component | Repository | License | Can modify | Can redistribute | Attribution | Stack | Visual quality | Recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| System icons | microsoft/fluentui-system-icons | **MIT** | yes | yes | keep MIT notice | SVG | 5/5 — Microsoft's own Fluent set | **DIRECT USE** ✅ vendored |
| UI font | microsoft/Selawik | **OFL 1.1** | yes (rename if modified) | yes | keep OFL, reserved name | TTF | 5/5 — metric-compatible Segoe UI substitute | **DIRECT USE** ✅ vendored |
| GTK theme | yeyushengfan258/Win11-gtk-theme | GPL-3.0 | yes | yes | GPL notice + source | GTK3/4 SCSS | 4/5 | **ADAPT** (tokens only) + ship for GTK apps |
| Icon theme | yeyushengfan258/Win11-icon-theme | GPL-3.0, derived from **Yaru** (per `AUTHORS`) | yes | yes | GPL + Yaru credit | SVG icon theme | 4/5 | **ADAPT** — candidate app/mime icon theme |
| Distro/build | Anduin2017/AnduinOS | GPL-3.0 | yes | yes | GPL notice | Ubuntu live-build, GNOME | 4/5 | **REFERENCE ONLY** (GNOME ≠ our stack) — but its **build system is a direct model** |
| Icon theme (alt) | vinceliuice/Fluent-icon-theme | GPL-3.0 | yes | yes | GPL + author credit | SVG + Xcursor | 5/5 — used by AnduinOS, actively maintained (last release 2025-08) | **ADAPT** — preferred app icon theme, also gives a **cursor theme** |
| KDE theme | vinceliuice/Fluent-kde | GPL-3.0 | yes | yes | GPL | Plasma/Kvantum | 4/5 | REFERENCE ONLY (we do not ship Plasma shell) |
| KDE theme | Jeysef/KDE-Windows-Modern | check per-asset | — | — | — | Plasma 6 + applets | 4/5 — closest full Win11 look for Plasma | REFERENCE ONLY (asset provenance mixed) |
| KDE theme | yeyushengfan258/Win11OS-kde | GPL-3.0 | yes | yes | GPL | Plasma | 3/5, last touched 2021 | REFERENCE ONLY |
| KDE theme | doncsugar/willow-theme | GPL-3.0 | yes | yes | GPL | Plasma | 3/5 | REFERENCE ONLY |
| Start menu | adhec/OnzeMenuKDE | GPL-3.0 | yes | yes | GPL | Plasma QML applet | 3/5 | **ADAPT** — QML layout logic is directly readable |
| Start menu | prateekmedia/Menu11 | GPL-2.0 | yes | yes | GPL | Plasma QML applet | 4/5 | **ADAPT** — closest Win11 Start behaviour in QML |
| Start menu | Eisteed/menu-11-next | GPL-2.0+ | yes | yes | GPL | Plasma QML applet | 4/5, active 2025 | **ADAPT** |
| Start menu | Zren/plasma-applet-tiledmenu | GPL-2.0+ | yes | yes | GPL | Plasma QML applet | 3/5 (Win10 tiles) | REFERENCE ONLY |
| Taskbar | LBCrion/sfwbar | GPL-3.0 | yes | yes | GPL | C, Wayland layer-shell | 3/5 look, 5/5 behaviour | **REFERENCE ONLY → mine for layer-shell + task grouping** |
| Taskbar/shell | wayle-rs/wayle | check | — | — | — | Rust + GTK4 | — | REFERENCE ONLY (wrong toolkit) |
| Cursors | quantum5/win2xcur | Apache-2.0 | yes | yes | notice | Python CLI | tool | **DIRECT USE as a tool** — but only on cursors we are licensed to convert |
| Cursors | vinceliuice/Fluent-icon-theme (cursors/) | GPL-3.0 | yes | yes | GPL | Xcursor | 4/5 | **ADAPT** — our cursor theme source |
| Distro | Zorin OS | mixed (core GPL, Pro proprietary) | partly | no (Pro parts) | — | GNOME | 5/5 polish | REFERENCE ONLY |
| Distro | Winux (ex-Linuxfx/Wubuntu) | **proprietary** | no | no | — | Kubuntu+KDE | 4/5 | **DO NOT USE** — paid PowerTools, trademark and 2022 activation-DB leak |

## 2. Win11-gtk-theme — what we extracted

Direct CSS transplant into Qt/QML is impossible (different property model), so the **values** were
read out of `src/_sass/_variables.scss` and `_colors.scss` and compared with our own token set:

| Parameter | Win11-gtk-theme | Zaldros today | Decision |
| --- | --- | --- | --- |
| Window radius | 16 px (round) / 10 px | 8 px panels, 10 px flyouts | keep ours (matches Microsoft's published radii), raise window radius to 10 px |
| Control radius | 10 px / 4 px | 6 px | keep |
| Menu radius | control + 3 px | 8 px | keep |
| Row height | 28 px menu item | 32 px | keep (Windows 11 menu rows are taller than this theme's) |
| Spacing unit | 6 px (4 px compact) | 4/8 px scale | keep |
| Dark surface | `#333333`, base `#2B2B2B`, titlebar `#202020`, panel `#1F1F1F` @0.8 | `#202020` / `#2C2C2C` / taskbar `#1C1C1C` @0.92 | **adopted panel translucency idea**, kept our darker Fluent values |
| Light surface | `#F2F2F2` bg, `#FFFFFF` base, panel `#F7F7F7` | `#F3F3F3` / `#FFFFFF` / `#F9F9F9` | ours matches Windows 11 more closely |
| Animation | 75 ms, `cubic-bezier(0, 0, 0.2, 1)` | 90/150 ms, standard easing | **adopted the 75 ms fast tier** for hover feedback |
| Shadows | Material elevation z1…z24 | 2-tier | **adopted a 3-tier scale** derived from their z2/z8/z16 |

Honest finding: this theme is a **Material-Design engine wearing a Windows skin** (ripples, Material
elevation). Copying it wholesale would have made Zaldros look like Material, not Windows 11 — which
is exactly why only measured values were taken. Ship it as the **GTK application theme** so GTK apps
match the shell, since we cannot style GTK from Qt.

## 3. Win11-icon-theme — audit

`AUTHORS` states the source is **yaru-icon-theme (Ubuntu)**, so provenance is clean and GPL-3 —
better than assumed in the previous cycle, where it was rejected as unverified. Coverage inspected
locally: actions 5203, status 1809, apps 1094, mimes 798, places 420, devices 305, preferences 214.

| Icon class | Verdict | Why |
| --- | --- | --- |
| Folder / places | **ADAPT** — strong candidate | Yaru-derived, GPL-3, complete |
| Mime types | **ADAPT** | complete set, Explorer needs it |
| Device icons | ADAPT | complete |
| Application icons | ADAPT (per icon) | third-party product marks stay under their own rights — we ship the theme, we do not claim the marks |
| Status / action / symbolic | **REPLACE** | Fluent UI System Icons (MIT) is Microsoft's own set and is a better match — already vendored |

Preferred alternative for the shipped icon theme: **vinceliuice/Fluent-icon-theme** (GPL-3, active
2025, ships cursors, already validated at distro scale by AnduinOS).

## 4. AnduinOS — what we must not reinvent

Cloned and read (61 build mods, `src/build.sh`, `config/*.json`). Findings that change our plan:

1. **Build system.** Plain `debootstrap` → chroot mods → `squashfs` → `xorriso` ISO, based on
   *live-custom-ubuntu-from-scratch*. It needs no container runtime and no bootc — it runs on an
   ordinary Ubuntu host, so **our ISO build can run on a normal GitHub Actions runner**. This is the
   single most valuable finding of the cycle and directly unblocks "no bootable image yet".
2. **Installer.** Ubiquity, patched (`21-ubiquity-mod`, `22-ubiquity-patch`) — a Windows-migrant
   installer does not have to be written from scratch.
3. **Windows-like desktop without a custom shell.** GNOME + Dash-to-Panel + ArcMenu + Fluent theme.
   Cheap, but the ceiling is the extensions' own limits — which is why Zaldros keeps its own shell.
4. **System defaults matter more than theming**: no snap, no MOTD spam, patched localization,
   dconf defaults, xdg-mime defaults, wallpaper and plymouth. We mirror this as a defaults layer.
5. **Sponsorship of upstream** (`OSS.md`: AnduinOS sponsors vinceliuice). Good practice; if we ship
   his icon or cursor themes, we credit and support upstream the same way.

## 5. Component map — the visual combination

```
Zaldros visual foundation
├── System icons ........ Fluent UI System Icons (Microsoft, MIT)      [vendored, in use]
├── UI font ............. Selawik (Microsoft, OFL 1.1)                 [vendored, in use]
├── App/mime icons ...... Fluent-icon-theme (GPL-3) or Win11-icon-theme (GPL-3, Yaru-derived)
├── Cursor .............. Fluent-icon-theme cursors (GPL-3)
├── GTK app styling ..... Win11-gtk-theme (GPL-3), shipped for GTK apps
├── Qt/QML styling ...... Zaldros Design System (ours; values informed by the audit above)
├── Window decorations .. KWin + our decoration (behaviour reference: Fluent-kde)
├── Taskbar ............. ours; layer-shell and task grouping reference: sfwbar
├── Start Menu .......... ours; QML behaviour reference: Menu11, menu-11-next, OnzeMenuKDE
├── System UI ........... ours (Zaldros services, settings, updates) — never borrowed
└── Build/installer ..... AnduinOS-style debootstrap+squashfs+xorriso, Ubiquity/Calamares
```

No single project is adopted wholesale; each slot takes the best legally usable option, and the
system logic under it stays ours (spec §12).

## 6. Does the Qt/QML architecture block the visual target?

No. This cycle the shell moved from hand-drawn strokes to Microsoft's own icons and font without any
architectural change, and QML gives us behaviour that theme packs cannot (real window management,
real launching, real system readouts). The one real risk is **GTK applications** looking foreign;
that is solved by shipping the GTK theme above, not by changing our toolkit. Recommendation:
**keep Qt 6 / QML**.
