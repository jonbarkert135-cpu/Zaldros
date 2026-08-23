# bedrock-hwinfo

Collects the hardware and system inventory that Bedrock Device Manager (spec PART 3 §8) and
Bedrock System Information (§13) display: CPU, memory, storage, network interfaces, displays,
batteries, firmware/board identity, kernel and OS.

Every field comes from a real kernel interface (`/proc/cpuinfo`, `/proc/meminfo`, `/sys/block`,
`/sys/class/net`, `/sys/class/drm`, `/sys/class/power_supply`, `/sys/class/dmi/id`). Anything that
cannot be read is reported as `unknown` — never guessed (§21: no fabricated hardware information).

```bash
python -m bedrock_hwinfo                 # markdown report
python -m bedrock_hwinfo --format json   # machine-readable, for the GUI
python -m bedrock_hwinfo --sysfs ./fixture/sys --proc ./fixture/proc   # testing
```

Standard library only. Tests: `python -m pytest tools/bedrock-hwinfo/tests`.
