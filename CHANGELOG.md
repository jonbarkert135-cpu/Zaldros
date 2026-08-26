# Changelog

All notable changes to Zaldros OS. Nothing here is a claim that a component has been booted or
benchmarked unless it says so explicitly (spec PART 1 §15).

## [Unreleased]

### Fixed
- UI font: the vendored Selawik has no Cyrillic, so the Russian interface was silently rendered in
  DejaVu Sans on every ISO. Replaced with PT Sans (OFL 1.1), chosen by measuring against the
  Windows 11 reference capture, installed system-wide with a fontconfig alias, and guarded by
  `tests/test_ui_font.py` (ADR-0011).

### Added
- `tools/visual/font_match.py` — ranks candidate UI fonts against real Segoe UI text cropped from
  the reference capture.
- Full specification PARTS 1–5 preserved in `spec/`.
- Combined-spec audit (`docs/SPEC_AUDIT.md`): 6 contradictions resolved, 8 gaps, 5 risks, 7 open questions.
- Architecture set: base distribution, compositor/toolkit, system apps, compatibility/hardware/security,
  performance, security, testing, risks, roadmap (renumbered to the spec's phases 0–14).
- Windows → Zaldros feature matrix (`docs/architecture/FEATURE_MATRIX.md`).
- `tools/zaldros-sysprobe` 0.1.0 — service/dependency/resource map.
- `tools/zaldros-hwinfo` 0.1.0 — real hardware inventory from `/proc` and `/sys`.
- `tools/zaldros-compat` 0.1.0 — compatibility registries with a CI gate rejecting unevidenced claims.
- `tools/zaldros-bench` 0.1.0 — BASELINE → CHANGE → BENCHMARK → COMPARE → ACCEPT/REVERT harness.
- `build/Containerfile.base`, `build/Containerfile.desktop` — **written, never built** (no build host).

### Known state
- No Zaldros image has been built or booted. Zero hardware evidence records. Zero performance baselines.
