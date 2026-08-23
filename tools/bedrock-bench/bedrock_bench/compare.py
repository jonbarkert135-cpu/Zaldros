"""BASELINE → CHANGE → BENCHMARK → COMPARE → ACCEPT / REVERT (spec PART 5 §1).

`decide()` turns two samples into an explicit verdict. The verdict is deliberately conservative:
a change is ACCEPTed only when it improves at least one metric beyond the noise threshold and
regresses none; anything else is REVERT or INCONCLUSIVE. Missing measurements never count as
improvements — an unmeasured metric makes the comparison INCONCLUSIVE rather than silently passing
(spec PART 1 §15).
"""

from __future__ import annotations

from dataclasses import dataclass

ACCEPT, REVERT, INCONCLUSIVE = "ACCEPT", "REVERT", "INCONCLUSIVE"

# Metrics where a lower value is better. Everything measured so far is lower-is-better.
LOWER_IS_BETTER = (
    "used_ram_mib", "loadavg_1m", "process_count", "running_services", "disk_used_mib",
    "boot_firmware_s", "boot_loader_s", "boot_kernel_s", "boot_initrd_s", "boot_userspace_s",
    "boot_total_s", "startup_cold_s", "startup_warm_s", "ui_latency_ms",
)

# Relative change smaller than this is treated as noise, not as a result.
DEFAULT_NOISE = 0.03


@dataclass
class MetricDelta:
    name: str
    baseline: float | None
    candidate: float | None
    delta: float | None = None
    relative: float | None = None
    verdict: str = INCONCLUSIVE
    reason: str = ""


def compare_metric(name: str, baseline, candidate, noise: float = DEFAULT_NOISE) -> MetricDelta:
    result = MetricDelta(name=name, baseline=baseline, candidate=candidate)
    if baseline is None or candidate is None:
        result.reason = "not measured on both sides"
        return result
    result.delta = round(candidate - baseline, 4)
    result.relative = round((candidate - baseline) / baseline, 4) if baseline else None
    lower_better = name in LOWER_IS_BETTER
    if result.relative is None:
        result.reason = "baseline is zero"
        return result
    if abs(result.relative) < noise:
        result.verdict = "UNCHANGED"
        result.reason = f"within {noise:.0%} noise threshold"
        return result
    improved = result.relative < 0 if lower_better else result.relative > 0
    result.verdict = "BETTER" if improved else "WORSE"
    result.reason = f"{result.relative:+.1%}"
    return result


def decide(baseline: dict, candidate: dict, noise: float = DEFAULT_NOISE) -> tuple[str, list[MetricDelta], str]:
    """Return (verdict, per-metric deltas, human-readable rationale)."""
    names = sorted(set(baseline) | set(candidate))
    deltas = [compare_metric(name, baseline.get(name), candidate.get(name), noise) for name in names]
    better = [d for d in deltas if d.verdict == "BETTER"]
    worse = [d for d in deltas if d.verdict == "WORSE"]
    missing = [d for d in deltas if d.verdict == INCONCLUSIVE]

    if worse:
        return (
            REVERT,
            deltas,
            "regression in " + ", ".join(f"{d.name} ({d.reason})" for d in worse),
        )
    if missing and not better:
        return REVERT if False else (
            INCONCLUSIVE,
            deltas,
            "nothing improved and " + ", ".join(d.name for d in missing) + " could not be measured",
        )
    if not better:
        return INCONCLUSIVE, deltas, "no metric moved beyond the noise threshold"
    if missing:
        return (
            INCONCLUSIVE,
            deltas,
            "improvements found but " + ", ".join(d.name for d in missing)
            + " could not be measured — measure before accepting",
        )
    return (
        ACCEPT,
        deltas,
        "improved " + ", ".join(f"{d.name} ({d.reason})" for d in better) + " with no regression",
    )


def to_markdown(verdict: str, deltas: list[MetricDelta], rationale: str,
                title: str = "Benchmark comparison") -> str:
    lines = [f"# {title}", "", f"**Verdict: {verdict}** — {rationale}", "",
             "| Metric | Baseline | Candidate | Delta | Result |",
             "| --- | ---: | ---: | ---: | --- |"]
    for d in deltas:
        fmt = lambda v: "—" if v is None else f"{v:g}"  # noqa: E731
        lines.append(
            f"| `{d.name}` | {fmt(d.baseline)} | {fmt(d.candidate)} | {fmt(d.delta)} | "
            f"{d.verdict} ({d.reason}) |"
        )
    lines += ["", "> An unmeasured metric never counts as an improvement (spec PART 1 §15)."]
    return "\n".join(lines) + "\n"
