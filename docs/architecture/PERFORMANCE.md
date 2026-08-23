# Performance strategy

Loop (spec §6): BASELINE → CHANGE → MEASURE → COMPARE → ACCEPT OR REVERT.

## Metrics and how they are measured
| Metric | Tool | Target (reference laptop, 8 GB, NVMe) |
|---|---|---|
| Boot to session | `systemd-analyze`, `systemd-analyze blame/critical-chain` | < 12 s firmware-excluded |
| Idle RAM after login | PSS sum via `smem`/`/proc/*/smaps_rollup` | < 900 MB (Desktop), < 600 MB (Legacy) |
| Idle CPU | 5-min average, `pidstat` | < 1 % |
| Start menu cold open | shell instrumentation timestamp | < 150 ms |
| Window drag frame time | KWin frame timings / `kwin_perf` | 99th pct under refresh interval |
| Update apply time | build tooling | < 90 s + reboot |

## Rules
1. No optimisation without a recorded baseline in `docs/state/measurements/`.
2. No service is removed until `zaldros-sysprobe` documents purpose, dependants and consequences.
3. Animations are capped by profile; PERFORMANCE > ANIMATION (PART 2 §19).
4. Search indexing is opt-in and scoped; no permanent full-disk indexer (PART 2 §4, §5).
5. Regressions >5 % on any metric block a merge.
