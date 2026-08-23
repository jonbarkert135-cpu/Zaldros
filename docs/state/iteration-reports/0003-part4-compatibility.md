# Iteration report 0003 — PART 4 integrated, compatibility evidence gate, image definitions

Format per spec PART 1 §16. Date: 2026-08-23.

**CURRENT OBJECTIVE** — Absorb PART 4 (applications, compatibility, hardware, power, security) and
make its hardest rule — §25, "never claim compatibility without evidence" — mechanically enforceable
rather than a good intention.

**RESEARCH** — Reviewed the delivery formats (Flatpak/AppImage/rpm/distrobox/Wine) against the
image-based base, and the hardware stack choices (Mesa vs NVIDIA proprietary, PipeWire, NetworkManager,
BlueZ, CUPS driverless, ntfs3 for Windows-formatted media). Noted that PART 4 §6 ("do not remove
drivers for performance") directly constrains the performance profiles from PART 1 §8: profiles may
change runtime behaviour only, never driver presence.

**DECISION** — `docs/architecture/COMPATIBILITY_AND_HARDWARE.md`: Flatpak-first delivery with
AppImage and distrobox supported; Wine/Proton as an optional, non-base component; Mesa default with a
separate NVIDIA image variant; PipeWire/NetworkManager/BlueZ/firewalld; no telemetry at all;
btrfs decision explicitly held open pending an ext4 comparison (that measurement *is* the §18 evidence);
shell components as restartable systemd user units so an app or applet crash cannot kill the session.

**IMPLEMENTATION** — `spec/PART_4.md` preserved. New component `tools/bedrock-compat` v0.1.0: two
registries (`data/applications.json`, `data/hardware.json`) plus a validator that rejects any positive
status without an evidence record containing date, build id, tester and result. `--check` is a CI job,
so an unevidenced claim fails the build. Also added `build/Containerfile.base` and
`build/Containerfile.desktop` with a build README.

**TEST** — 11 new unit tests: status vocabulary enforcement, missing/incomplete/badly-dated evidence,
the per-kind evidence rules, duplicate ids, summary and report rendering, the shipped registries'
validity, and both CLI exit codes (0 on the honest shipped data, 1 on a fabricated "tested" claim).

**RESULT** — `31 passed in 0.14s`. `--check` on shipped data: "ok [apps] 8 entries, ok [hardware] 13
entries, all claims evidenced". Every one of the 13 hardware entries is `untested` — which is the
truthful state, since no Bedrock image has ever been booted.

**PROBLEMS** — No podman and no `/dev/kvm` in this environment, so the two Containerfiles cannot be
built or booted here. Writing them without building them risks exactly the false success §15 forbids.

**FIX** — Both files and the build README carry an explicit "WRITTEN, NOT YET BUILT" banner, the
project state lists the missing build host as the current blocker, and the image build is defined as a
CI job so it is executed the moment a runner is available. No document claims a working image.

**METRICS** — 31/31 tests, 0.14 s. Three shipping tools, zero external dependencies. Hardware
evidence records: 0 (honest).

**NEXT** — PART 5 integration, and, as soon as a build host exists: build `bedrock-base`, boot it in
QEMU, run `bedrock-sysprobe` + `bedrock-hwinfo` inside it and record the first evidence entries.
