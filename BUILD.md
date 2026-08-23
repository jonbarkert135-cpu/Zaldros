# Building Bedrock Linux

**Status: the build has never been executed.** These are the intended, reviewed commands; no image has
been produced yet because no build host with `podman` and `/dev/kvm` is available to the project
(`docs/state/PROJECT_STATE.md`). Nothing in this file may be quoted as evidence that Bedrock builds.

## Requirements
- Linux host, `podman` 4+, ~20 GB free disk
- For the VM test: `qemu-system-x86_64` and `/dev/kvm`

## Build
```bash
podman build -t bedrock-base    -f build/Containerfile.base    .
podman build -t bedrock-desktop -f build/Containerfile.desktop .
```

## Bootable image
```bash
podman run --rm -it --privileged -v .:/output \
  quay.io/centos-bootc/bootc-image-builder --type qcow2 localhost/bedrock-desktop
```

## VM test (the gate for Phase 1)
```bash
qemu-system-x86_64 -enable-kvm -m 4096 -smp 4 -bios /usr/share/OVMF/OVMF_CODE.fd \
  -drive file=output/qcow2/disk.qcow2,format=qcow2
```
Inside the VM, record the first real evidence:
```bash
python3 -m bedrock_sysprobe -o service-map.md
python3 -m bedrock_hwinfo   -o inventory.md
python3 -m bedrock_bench collect --label phase1-baseline -o baseline.json
```

## Tests
```bash
python -m pytest tools -q
python -m bedrock_compat --check   # from tools/bedrock-compat
```
