# Building Zaldros OS

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

**What that evidence is not.** Nothing has run on real hardware: no laptop, no GPU that is not
virtio, no Wi-Fi or Bluetooth radio, no installer. Every "works" in this repository means "works
in QEMU on a GitHub runner" until a machine says otherwise.

## Requirements for the ISO build

- A Linux host where you are **really root** (or a user namespace with a full `/etc/subuid`
  range). `debootstrap`/apt configure system users and `chown` them; a namespace that maps a
  single UID fails with `dpkg-statoverride: error setting ownership … Invalid argument`, which
  kills the `apt-install` step after the packages are already unpacked.
- `squashfs-tools`, `xorriso`, `grub-pc-bin`, `grub-efi-amd64-bin`, `mtools`, ~25 GB free disk.
- For the boot test: `qemu-system-x86_64`, `ovmf`, `socat`, `imagemagick`, and `/dev/kvm`.
  Without KVM the boot test still runs, but slowly — TCG times must not be quoted as boot times.

## Build and boot-test

```bash
./build/iso/build-iso.sh full zaldros-full.iso      # or: services | legacy
./build/iso/boot-test.sh  zaldros-full.iso modern results
python3 ./build/iso/report.py results               # PASS/FAIL matrix; exit 1 if anything failed
```

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
