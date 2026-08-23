# Testing strategy

## Levels
1. **Unit** — per component (pytest/cargo test/QtTest). Runs on every push.
2. **Build** — OS image builds reproducibly in CI; artefact versioned.
3. **VM boot smoke** — QEMU boot, session starts, network up, no failed units (`systemctl --failed`).
4. **Functional** — scripted UX workflows from PART 2 §22 (open Start, search app, connect Wi-Fi,
   change display settings, install app, update system) driven via the shell's test IPC.
5. **Performance** — metrics from `docs/architecture/PERFORMANCE.md`, compared to stored baselines.
6. **Visual regression** — reference screenshot → implementation screenshot → geometry/spacing/
   typography/colour diff → similarity score (PART 2 §21). Score is stored per component and may not drop.
7. **Regression** — full suite before every milestone tag.
8. **Hardware** — matrix of real machines from Phase 4 (Intel/AMD/NVIDIA, laptop/desktop, HiDPI, multi-monitor).

## Non-negotiable
A feature is complete only after implementation + build + functional test + regression test +
verification. Screenshots and successful builds are not evidence of completion (PART 1 §15).
