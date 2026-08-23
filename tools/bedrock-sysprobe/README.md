# bedrock-sysprobe

Generates the service / dependency / resource map required by the Bedrock Linux specification
(PART 1 §7) and consumed by the performance profiles (§8).

For every systemd service it records: description, active state, enablement, PSS memory of the
main process, accumulated CPU time, boot activation time (`systemd-analyze blame`), the units that
depend on it, and whether nothing requires it.

```bash
python -m bedrock_sysprobe                       # markdown table on stdout
python -m bedrock_sysprobe --format json -o map.json
python -m bedrock_sysprobe --unit sshd.service   # single unit
```

Standard library only — runs inside a minimal image with no extra packages.
Run tests with `python -m pytest tools/bedrock-sysprobe/tests`.
