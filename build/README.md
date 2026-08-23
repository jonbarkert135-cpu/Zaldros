# Building Zaldros OS images

Two image targets:

| Target | File | Contents |
| --- | --- | --- |
| `zaldros-base` | `Containerfile.base` | core system only — no shell. Proves the §5 layer separation. |
| `zaldros-desktop` | `Containerfile.desktop` | base + KWin/Plasma Wayland session + reused apps |

```bash
podman build -t zaldros-base    -f build/Containerfile.base    .
podman build -t zaldros-desktop -f build/Containerfile.desktop .
# bootable disk image / ISO:
podman run --rm -it --privileged -v .:/output \
  quay.io/centos-bootc/bootc-image-builder --type qcow2 localhost/zaldros-desktop
```

**These definitions have never been built or booted.** They require a Linux host with `podman` and,
for the QEMU boot test, `/dev/kvm`. Until a build host exists, nothing in this directory may be
described as working (spec PART 1 §15 — no false success).
