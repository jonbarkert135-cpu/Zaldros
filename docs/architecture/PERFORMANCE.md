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

## Idle shell overhead: polling vs. the backend layer (ADR-0014)
Measured 2026-08-27 with `tools/zaldros-bench/backend_overhead.py`, which runs both modes in the
same process and the same run, so the numbers are comparable to each other and to nothing else.

| 300 s idle, no surface open | legacy (polling) | backend (events) |
|---|---|---|
| CPU seconds | 0.11 | < 0.01 (below this kernel's 10 ms accounting resolution) |
| CPU ms per minute | 22.0 | < 2 |
| `/proc` reads | 1200 | 0 |
| model `changed` signals | 300 | 5 (clock ticks only) |

What changed: the shell had one 1 s timer reading `/proc/stat` and `/proc/meminfo` and emitting a
repaint every second whether or not anything was on screen. Now hardware state arrives from D-Bus
`PropertiesChanged`, the clock is a single-shot timer re-armed to the next minute boundary and only
emits when the displayed text changes, and the CPU/RAM meters are reference-counted: they sample
only while the Start menu or the game bar's performance panel is open.

Caveats recorded honestly: `voluntary_ctxt_switches` never increments under this sandbox kernel
(gVisor), so that counter is unusable here and the tool prints a note instead of a false zero; and
this is a sandbox, not the reference laptop — the ratio is the result, the absolute CPU figure is
not. Raw output: `docs/state/measurements/2026-08-27-backend-overhead.md`.
