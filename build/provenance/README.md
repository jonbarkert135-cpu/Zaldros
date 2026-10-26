# Build provenance and clean-room boundaries

This is an inventory and a shipping control, **not legal clearance**. Known gaps
remain public-release blockers. Existing assets have not been silently relicensed,
replaced or described as original Zaldros artwork.

## Vendored assets

`assets.json` records each of the 158 tracked asset files by path, SHA256, component
and shipping decision. It records source/license evidence and unresolved ancestry
at the component level. 154 files are staged; three research reference files and
the wallpaper generator are excluded. Known generated Python caches are ignored,
never staged. New non-cache assets or a changed hash fail validation until reviewed.

```bash
python3 build/iso/stage-assets.py
python3 build/iso/stage-assets.py --dest /tmp/zaldros-assets-new
```

The destination must not exist. The ISO uses this same helper and retains a copy
of the inventory as `/opt/zaldros/assets/PROVENANCE.json`. This stops the previous
whole-tree `assets/` copy from shipping the Windows reference PNG or future
unreviewed artwork. Research material remains in the repository for analysis;
exclusion from the ISO does not establish redistribution rights for the repository.

Current gaps:

- Exact original upstream revisions were not recorded for the selected app/place/
  Fluent System Icons SVGs and PT Sans. Local hashes establish which bytes are
  used now, not historical provenance or a publisher's signature.
- The fallback Windows-Eleven 4.8.8 archive is actually installed by the theme
  installer. It is not merely research. Its 33,112 members were enumerated without
  extraction; no absolute/traversal member name was found. No exact LICENSE,
  LICENSE.txt, COPYING, AUTHORS or COPYRIGHT notice file was found inside the
  archive. Per-file licensing and ancestry remain unresolved. The store's GPL
  claim does not clear every icon; a project notice is not a substitute for the
  upstream license/source obligations. Obtain a verifiable upstream notice/source
  or a reviewed replacement before a public release.
- Kvantum's attribution covers a larger upstream collection than the selected
  four theme files. Do not assume all assets mentioned there are bundled here,
  or that every upstream licensing gap necessarily belongs to these four files.
- Third-party app/place SVGs remain derivative upstream work. Preserve notices
  and corresponding-source obligations; assembling a Zaldros theme does not
  transfer authorship.

## Downloaded cursor source

`system/theme/fetch-sources.sh` defaults to full commit
`c8a244f571ef8fb47812bdc9dbce76546cedce69` of
<https://github.com/vinceliuice/Fluent-icon-theme>. This exact commit was fetched
and checked out during P02. Overrides must also be full 40-character commits;
failed fetches abort instead of silently using an old checkout. The installed
`cursors/LICENSE` is GPL-3.0 text, SHA256
`605e9047a563c5c8396ffb18232aa4304ec56586aee537c45064c6fb425e44ad`.
This pin establishes reproducible source identity, not an upstream signed release
or legal certification of the whole repository.

## Root filesystem trust

`build/iso/fetch-rootfs.py` downloads SHA256SUMS and its detached signature over
HTTPS. It verifies OpenPGP against the independent full fingerprint in
`ubuntu-cdimage-policy.json`, then downloads/hashes the named archive. Only then
does tar run, into a temporary sibling of the destination. A failed verification
or extraction cannot leave a partial rootfs at the build's destination.

Default authority: Ubuntu CD Image Automatic Signing Key (2012), fingerprint
`843938DF228D22F7B3742BC0D94AA3F0EFE21092`. The policy cites Ubuntu's published
verification tutorial. The keyserver response is merely key material: a successful
GnuPG verification must still match that independently pinned authority. A trusted
local keyring may be supplied with `--keyring`; this does not override the signer pin.
No user GnuPG keyring, trustdb, automatic key retrieval or insecure curl option is used.

Needs Python 3.11+, curl, GnuPG and tar. A signing-key rotation is an explicit policy
update after verifying Ubuntu's authoritative announcement, never acceptance of
whichever key a new download supplies. Signed manifest/signature/digest evidence
is retained in the build debug directory. Network/signature/hash failure stops the
build; there is no automatic debootstrap fallback or partially reused tree.

Real OpenPGP fixtures test valid extraction, tampering, an untrusted signer, missing/
duplicate entries, absent signatures and signed-but-malformed tar. These tests use
locally generated keys and no network/root; they do not establish that the current
Ubuntu release still uses the pinned key or that the live endpoint is reachable.
The live check was initially blocked by egress policy. After connectivity became
available, the production helper authenticated and extracted the real Ubuntu
26.04 amd64 rootfs on 2026-10-26. The full fingerprint was also checked against the
official Ubuntu verification tutorial over HTTPS. Archive SHA256:
`046fcabb7f16f45a80ae11824664f2a07e01386c6fb1ed9dc1e225a66a6553a2`.
The [signed manifest and receipt](../../docs/state/evidence/p02-rootfs/README.md)
are retained in the repository. This establishes artifact authentication and
extraction, not successful boot or hardware support.

## System packages and code

The active ISO recipe lists BASE/EXTRA apt packages, obtains dependencies through
Ubuntu's signed apt metadata and retains `/usr/share/doc/*/copyright` in the rootfs.
`collect_debug` records exact installed binary-package versions in
`installed-packages.txt` for each build. Until a build runs, this is a recipe, not
a current release SBOM or a bit-for-bit reproducible snapshot.

Major runtime sources: Linux kernel, systemd/logind, Ubuntu userspace, KWin/KDE,
Qt/PySide6, NetworkManager, PipeWire/WirePlumber, UDisks, BlueZ, polkit, portals,
KScreen/PowerDevil where installed. Their installed versions/licenses come from
the selected variant's package inventory and upstream copyright files, not a
single license inherited from Zaldros. Zaldros code is GPL-3.0-or-later.
LibreOffice/UNO Office prototypes are in the repository but are not copied by the
current ISO recipe. Wine/Proton integration remains separate work. Legacy Fedora
Containerfiles are not evidence for the active Ubuntu dependency graph.

Release remains blocked on provenance gaps, current-source ISO build/boot acceptance
and the functional gates in the development plan. Successful artifact verification
does not resolve those independent requirements.
