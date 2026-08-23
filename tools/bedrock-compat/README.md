# bedrock-compat

Keeps Bedrock Linux honest about what works. Two registries live in `data/`:

- `applications.json` — Windows/Linux applications classified as `native`, `compatible`, `partial`,
  `unsupported` or `untested` (spec PART 4 §3).
- `hardware.json` — hardware classified as `tested`, `partially_tested`, `untested` or `known_issue`
  (spec PART 4 §25).

A positive claim without at least one evidence record (date, build, tester, result) is a **build
failure**, not a warning:

```bash
python -m bedrock_compat --check            # CI gate
python -m bedrock_compat --report hardware  # markdown matrix for the docs/Store
```

`untested` is always an acceptable answer. Inventing compatibility is not.
