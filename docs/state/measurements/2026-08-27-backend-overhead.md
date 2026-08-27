# 2026-08-27 — idle shell overhead, polling vs. backend

Command:

    QT_QPA_PLATFORM=offscreen shell/zaldros-shell/.venv/bin/python \
      tools/zaldros-bench/backend_overhead.py --seconds 300 --json out.json

Host: build sandbox (gVisor kernel), not the reference laptop.

                             legacy       backend
    elapsed_seconds          299.94         299.8
    cpu_seconds                0.11           0.0
    cpu_per_minute_ms          22.0           0.0
    voluntary_ctx                 0             0
    proc_reads                 1200             0
    signals                     300             5

Notes emitted by the tool:
- legacy: `voluntary_ctx` stayed 0 — this kernel does not increment `voluntary_ctxt_switches`
  (seen under gVisor); the figure is unusable here, use `proc_reads` and `signals`.
- backend: `cpu_seconds` is below this kernel's accounting resolution (10 ms); read it as
  "< 10 ms", not as zero.

A 60 s run the same evening gave the same shape: legacy 0.03 s CPU / 240 proc reads / 60 signals,
backend < 0.01 s / 0 / 1.

Machine-readable copy: `2026-08-27-backend-overhead.json`.
