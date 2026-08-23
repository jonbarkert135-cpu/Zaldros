# Compatibility

See `docs/architecture/COMPATIBILITY_AND_HARDWARE.md` for the architecture and
`tools/zaldros-compat/data/` for the machine-readable registries. Generate the current matrices:

```bash
cd tools/zaldros-compat
python -m zaldros_compat --report hardware
python -m zaldros_compat --report apps
```

All 13 hardware entries are currently `untested` and no application carries a compatibility claim,
because no Zaldros image has been booted. That is the honest state, not an omission (spec PART 4 §25).
