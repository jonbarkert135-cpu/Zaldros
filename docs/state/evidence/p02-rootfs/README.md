# Ubuntu rootfs authentication evidence — 2026-10-26

Production helper from code commit `b133e9611a45c22a8f45f564b86471af82e74740`,
merged into main via PR #1 / `6168e9bd5f55d879630d34b4e1ae0509ec1b3eb4`.

Executed without root:

```bash
python3 build/iso/fetch-rootfs.py \
  --url https://cdimage.ubuntu.com/ubuntu-base/releases/26.04/release/ubuntu-base-26.04-base-amd64.tar.gz \
  --root /tmp/zaldros-p02-live-rootfs \
  --evidence /tmp/zaldros-p02-live-evidence
```

Exit 0. The helper verified the detached OpenPGP signature against the independently
pinned full Ubuntu CD-image primary fingerprint, checked the archive SHA256, and
extracted it. `/etc/os-release` in the extracted tree identifies Ubuntu 26.04 LTS,
Resolute Raccoon. No chroot, boot or hardware test was performed by this command.

The full primary fingerprint was also confirmed in the official HTTPS
[Ubuntu verification tutorial](https://ubuntu.com/tutorials/how-to-verify-ubuntu).
Key material came from the HTTPS keyserver specified in the checked-in signing policy;
its authenticity was checked by fingerprint, not assumed from keyserver delivery.

- `SHA256SUMS`: the exact signed upstream manifest retrieved in this run.
- `SHA256SUMS.gpg`: its detached upstream signature, retained unmodified.
- `rootfs-verification.json`: the helper's successful extraction receipt.

Archive digest: `046fcabb7f16f45a80ae11824664f2a07e01386c6fb1ed9dc1e225a66a6553a2`.
The multiarchitecture manifest may contain other filenames; only the selected amd64
artifact was downloaded and checked. These files do not prove a reproducible ISO,
a successful Wayland session, installed-system recovery or legal clearance of assets.

## Remote workflow and published reports

- `main-ci.json`: [CI run 40333302969](https://github.com/jonbarkert135-cpu/Zaldros/actions/runs/40333302969),
  all five jobs SUCCESS on source `6168e9b`.
- `main-iso.json`: [ISO run 40333303076](https://github.com/jonbarkert135-cpu/Zaldros/actions/runs/40333303076),
  all 12 jobs SUCCESS: three builds and nine boot matrix jobs.
- `vm-report-summary.json`: nine published boot reports, each with BOOT PASS,
  plus host/guest per-step results and the exact diagnostic-branch commit read.
  Original reports are in the corresponding `ci-logs-boot-*` Git branches.

The diagnostic refs are mutable, so commit IDs are retained. The reports themselves
do not embed source SHA; workflow metadata supplies the run's source identity.
Current-date reports were selected after job publication; an old August report
was excluded until the final legacy/mid job published its new report.
The repository report tool was run against all nine selected reports and exited 0.

**Known acceptance gap:** legacy screenshot steps report FAIL in all three
profiles. The host-driven Start/taskbar/Alt+Tab/task-view steps report PASS;
guest Start/Alt+Tab entries are BLOCKED because the host owns them. Frame stability
is separately BLOCKED. `report.py` currently checks only boot status for its exit
code. Therefore the green workflow does not establish that every UI function works.
This gate defect and the minimal variant's missing screenshot capability remain
open work; neither was hidden or converted into a passing feature.
