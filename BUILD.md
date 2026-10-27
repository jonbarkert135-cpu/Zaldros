# Building Zaldros OS

Latest recorded build-input validation: [P02 evidence](docs/state/evidence/p02-rootfs/README.md),
source `6168e9b`, workflow `40333303076`: three ISO builds and nine boot jobs succeeded.
The guest screenshot step reports FAIL for legacy variants, despite green jobs;
see the retained per-step summary. This is not a completed desktop acceptance gate.
The dated CI account below remains historical context.

The [current functional gate](docs/state/decisions/ADR-0026-functional-ci-acceptance.md)
requires boot facts and all eleven host/guest UI checks to pass. Failed or missing
UI results now fail the report command and CI. Spectacle/portal screenshot support
is included in every variant; new build/boot evidence is recorded in PROGRESS.md.

The live ISO is built by `build/iso/build-iso.sh` (Ubuntu 26.04 base rootfs → apt → squashfs →
`grub-mkrescue`) and boot-tested by `build/iso/boot-test.sh` under QEMU/KVM. The container/bootc
recipe further down belongs to the superseded Fedora base (**ADR-0009**) and is kept only because
CI still builds those images.

## Status: the ISO builds, and the built ISO boots — in CI

Evidence, `iso` workflow run **33157358995** on commit `b85017e` (2026-08-28), all 12 jobs green:

| job | result |
| --- | --- |
| `build (legacy)` | ISO produced, 5 min 11 s |
| `build (services)` | ISO produced, 5 min 40 s |
| `build (full)` | ISO produced, 5 min 46 s — artifact `iso-full`, 3 038 491 745 B (≈2.83 GiB) |
| `boot (variant × profile)` | 9/9 booted: legacy/services/full × low/mid/modern |

The runners report `KVM available`, so those boots are accelerated, not TCG. `full/modern`
(8 vCPU, 16 GiB, virtio-vga) reported `PASS`, and the host-side UI drive measured `start_open`,
`start_close`, `taskbar_response` and `alt_tab` as PASS with a second real window
(`Home — Dolphin`) on screen and an empty `qmp_errors` list.

### Where a CI job's evidence is kept

Every build and boot job publishes what it saw to its own branch — `ci-logs-<variant>` for builds
(`steps.tsv`, `environment.txt`, `el-torito.txt`, per-step logs) and
`ci-logs-boot-<variant>-<profile>` for boots (JSON reports, serial log, PNG screendumps). No
repository admin rights are needed to read them, unlike job artifacts:

```bash
git fetch origin '+refs/heads/ci-logs-*:refs/remotes/origin/ci-logs-*'
git show origin/ci-logs-boot-full-modern:zaldros-full-modern-host.json
```

Publishing goes through `build/iso/publish-evidence.sh`, which retries the `cannot lock ref` race
that two overlapping runs cause and fails loudly if nothing lands (**ADR-0024**). The UEFI half of
each ISO is verified from the El Torito catalogue by `build/iso/verify-iso.py`: no UEFI boot image
means the build fails, an unreadable report means `UNVERIFIED` — never a pass.

**What that evidence is not.** Nothing has run on real hardware: no laptop, no GPU that is not
virtio, no Wi-Fi or Bluetooth radio, no installer. Every "works" in this repository means "works
in QEMU on a GitHub runner" until a machine says otherwise.

## Automatic ISO input coverage

Repository branch pushes trigger the ISO workflow for changes in `backend/`,
`apps/`, `assets/`, `system/`, `shell/`, `build/iso/`, `build/provenance/`, the
shipped `tools/collect-logs.sh`, or the active ISO workflow itself. Documentation
and the historical Fedora Containerfiles retain ordinary CI without rebuilding
the Ubuntu ISO. Manual workflow dispatch remains available.

The tools regression checks the push filter against actual `$REPO` recipe inputs,
the asset inventory and all app sources. It rejects filters that miss an input,
checks the reference workflow copy, and supports the filter's intentionally simple
literal-path/directory-`/**` syntax. The workflow keeps its path list JSON-compatible
so this check needs no new parser dependency.

This extends the existing repository-push/manual workflow; it does not introduce
pull-request-event execution with diagnostic-branch write credentials. Branch
pushes in this repository run before their PR is merged. Native GitHub path-filter
behavior still applies. Selecting `apps/**` does not install the Office frontends
in the ISO: their packaging/integration remains separate work, and their current
real-engine CI runs on Ubuntu 24.04.

## Requirements for the ISO build

P02 authenticates the Ubuntu rootfs checksum manifest and archive before extraction;
download or verification failure stops the build without fallback. See
[build provenance](build/provenance/README.md) for signing policy, evidence and
remaining live-validation/provenance gaps. Research references are excluded from
the staged ISO assets by an explicit hash inventory.

- A Linux host where you are **really root** (or a user namespace with a full `/etc/subuid`
  range). `debootstrap`/apt configure system users and `chown` them; a namespace that maps a
  single UID fails with `dpkg-statoverride: error setting ownership … Invalid argument`, which
  kills the `apt-install` step after the packages are already unpacked.
- `squashfs-tools`, `xorriso`, `grub-pc-bin`, `grub-efi-amd64-bin`, `mtools`, ~25 GB free disk.
- Python 3.11+, `curl`, `gnupg`, `tar`; HTTPS access to `cdimage.ubuntu.com`
  and `keyserver.ubuntu.com` for authenticated rootfs retrieval.
- For the boot test: `qemu-system-x86_64`, `ovmf`, `socat`, `imagemagick`, and `/dev/kvm`.
  Without KVM the boot test still runs, but slowly — TCG times must not be quoted as boot times.

## Build and boot-test

```bash
./build/iso/build-iso.sh full zaldros-full.iso      # or: services | legacy
./build/iso/boot-test.sh  zaldros-full.iso modern results
python3 ./build/iso/report.py results               # PASS/FAIL matrix; exit 1 if anything failed
```

For a single CI target, specify `--variant full --profile modern` (or the selected
variant/profile) so a stale or different target cannot validate the job. Historical
boot-only reports without complete UI measurements no longer satisfy this gate.

`build-iso.sh` writes `steps.tsv` next to the ISO — one line per step with its exit code, which is
the fastest way to see how far a failed build got.

## Tests

```bash
python -m pytest tools -q                                 # tools
cd shell/zaldros-shell && QT_QPA_PLATFORM=offscreen python -m pytest tests -q   # shell + backend
python -m zaldros_compat --check                          # from tools/zaldros-compat
```

## Container images (superseded base, ADR-0009)

```bash
podman build -t zaldros-base    -f build/Containerfile.base    .
podman build -t zaldros-desktop -f build/Containerfile.desktop .
podman run --rm -it --privileged -v .:/output \
  quay.io/centos-bootc/bootc-image-builder --type qcow2 localhost/zaldros-desktop
```

Inside a booted image, record hardware evidence:

```bash
python3 -m zaldros_sysprobe -o service-map.md
python3 -m zaldros_hwinfo   -o inventory.md
python3 -m zaldros_bench collect --label phase1-baseline -o baseline.json
```
