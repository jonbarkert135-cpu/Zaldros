# bedrock-bench

Implements the spec PART 5 §1 loop as a tool instead of a habit:

```
BASELINE → CHANGE → BENCHMARK → COMPARE → ACCEPT / REVERT
```

```bash
python -m bedrock_bench collect --label baseline --commit $(git rev-parse --short HEAD) -o baseline.json
# ... make the change, rebuild, reboot the VM ...
python -m bedrock_bench collect --label candidate -o candidate.json
python -m bedrock_bench compare baseline.json candidate.json --strict
```

Measured: used RAM, 1-minute load, process count, running services, and every systemd boot stage
(firmware, loader, kernel, initrd, userspace, total). Metrics that cannot be measured in the current
environment are reported as `null` **with the reason**, and a null never counts as an improvement —
a comparison with missing data returns `INCONCLUSIVE`, not `ACCEPT`.
