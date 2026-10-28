# zaldros-bench

Implements the spec PART 5 §1 loop as a tool instead of a habit:

```
BASELINE → CHANGE → BENCHMARK → COMPARE → ACCEPT / REVERT
```

```bash
python -m zaldros_bench collect --label baseline --commit $(git rev-parse --short HEAD) -o baseline.json
# ... make the change, rebuild, reboot the VM ...
python -m zaldros_bench collect --label candidate -o candidate.json
python -m zaldros_bench compare baseline.json candidate.json --strict
```

Measured: used RAM, 1-minute load, process count, running services, and every systemd boot stage
(firmware, loader, kernel, initrd, userspace, total). Metrics that cannot be measured in the current
environment are reported as `null` **with the reason**, and a null never counts as an improvement —
a comparison with missing data returns `INCONCLUSIVE`, not `ACCEPT`.

For the P04 update-check fault case, use the shell Python environment (Qt required):

```bash
mkdir -p /tmp/zaldros-update-baseline
git archive b86f4a95c49ae6676a2c41cf46a53d1199becb07 backend | tar -x -C /tmp/zaldros-update-baseline
.venv/bin/python tools/zaldros-bench/update_check_latency.py --mode synchronous --backend-root /tmp/zaldros-update-baseline/backend --out /tmp/update-baseline.json
.venv/bin/python tools/zaldros-bench/update_check_latency.py --mode worker --out /tmp/update-worker.json
PYTHONPATH=tools/zaldros-bench .venv/bin/python -m zaldros_bench compare /tmp/update-baseline.json /tmp/update-worker.json --strict
```

This measures only the maximum Qt heartbeat gap while a private test service is
slow; an ACCEPT applies to that metric/scenario, not OS readiness or general CPU,
RAM, network-update performance, or VM frame pacing.
