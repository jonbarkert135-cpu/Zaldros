# Changelog

All notable changes to Bedrock Linux. Nothing here is a claim that a component has been booted or
benchmarked unless it says so explicitly (spec PART 1 §15).

## [Unreleased]

### Added
- Full specification PARTS 1–5 preserved in `spec/`.
- Combined-spec audit (`docs/SPEC_AUDIT.md`): 6 contradictions resolved, 8 gaps, 5 risks, 7 open questions.
- Architecture set: base distribution, compositor/toolkit, system apps, compatibility/hardware/security,
  performance, security, testing, risks, roadmap (renumbered to the spec's phases 0–14).
- Windows → Bedrock feature matrix (`docs/architecture/FEATURE_MATRIX.md`).
- `tools/bedrock-sysprobe` 0.1.0 — service/dependency/resource map.
- `tools/bedrock-hwinfo` 0.1.0 — real hardware inventory from `/proc` and `/sys`.
- `tools/bedrock-compat` 0.1.0 — compatibility registries with a CI gate rejecting unevidenced claims.
- `tools/bedrock-bench` 0.1.0 — BASELINE → CHANGE → BENCHMARK → COMPARE → ACCEPT/REVERT harness.
- `build/Containerfile.base`, `build/Containerfile.desktop` — **written, never built** (no build host).

### Known state
- No Bedrock image has been built or booted. Zero hardware evidence records. Zero performance baselines.
