import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from zaldros_bench.compare import (  # noqa: E402
    ACCEPT, INCONCLUSIVE, REVERT, compare_metric, decide, to_markdown,
)
from zaldros_bench.metrics import (  # noqa: E402
    collect, count_processes, parse_duration, parse_meminfo, parse_systemd_analyze,
    read_loadavg, used_ram_mib,
)
from zaldros_bench.__main__ import main  # noqa: E402

ANALYZE = ("Startup finished in 4.512s (firmware) + 2.104s (loader) + 1.298s (kernel) + "
           "912ms (initrd) + 3.007s (userspace) = 11.833s graphical.target reached after 9.211s "
           "in userspace")


def test_parse_duration_units():
    assert parse_duration("812ms") == 0.812
    assert parse_duration("3.007s") == 3.007
    assert parse_duration("1min 4.231s") == 64.231
    assert parse_duration("nothing here") is None


def test_parse_systemd_analyze_stages():
    stages = parse_systemd_analyze(ANALYZE)
    assert stages["firmware"] == 4.512
    assert stages["loader"] == 2.104
    assert stages["kernel"] == 1.298
    assert stages["initrd"] == 0.912
    assert stages["userspace"] == 3.007
    assert stages["total"] is not None


def test_parse_meminfo_and_used_ram():
    meminfo = parse_meminfo("MemTotal:  16384000 kB\nMemAvailable: 12288000 kB\nBogus: x\n")
    assert meminfo["MemTotal"] == 16384000
    assert used_ram_mib(meminfo) == 4000.0
    assert used_ram_mib({"MemTotal": 1}) is None


def test_read_loadavg():
    assert read_loadavg("0.42 0.31 0.28 1/512 9999") == 0.42
    assert read_loadavg("") is None


def test_count_processes_on_real_proc():
    count = count_processes()
    assert count is None or count > 0
    assert count_processes("/nonexistent-proc") is None


def test_collect_marks_unavailable_metrics_instead_of_guessing():
    sample = collect("test")
    assert sample.label == "test"
    assert "used_ram_mib" in sample.metrics
    for name, value in sample.metrics.items():
        if value is None:
            assert any(note.startswith(f"{name}:") for note in sample.unavailable), name
    assert json.loads(sample.to_json())["metrics"] == sample.metrics


def test_compare_metric_noise_threshold():
    assert compare_metric("used_ram_mib", 1000, 1010).verdict == "UNCHANGED"
    assert compare_metric("used_ram_mib", 1000, 800).verdict == "BETTER"
    assert compare_metric("used_ram_mib", 1000, 1200).verdict == "WORSE"
    assert compare_metric("used_ram_mib", None, 800).verdict == INCONCLUSIVE


def test_decide_accepts_clear_improvement():
    verdict, _, rationale = decide({"used_ram_mib": 1000}, {"used_ram_mib": 800})
    assert verdict == ACCEPT
    assert "used_ram_mib" in rationale


def test_decide_reverts_on_any_regression():
    verdict, _, _ = decide(
        {"used_ram_mib": 1000, "boot_total_s": 10.0},
        {"used_ram_mib": 800, "boot_total_s": 14.0},
    )
    assert verdict == REVERT


def test_missing_measurement_never_becomes_an_improvement():
    verdict, _, rationale = decide(
        {"used_ram_mib": 1000, "boot_total_s": 10.0},
        {"used_ram_mib": 800, "boot_total_s": None},
    )
    assert verdict == INCONCLUSIVE
    assert "boot_total_s" in rationale


def test_decide_inconclusive_when_nothing_moves():
    verdict, _, _ = decide({"used_ram_mib": 1000}, {"used_ram_mib": 1005})
    assert verdict == INCONCLUSIVE


def test_markdown_report():
    verdict, deltas, rationale = decide({"used_ram_mib": 1000}, {"used_ram_mib": 800})
    report = to_markdown(verdict, deltas, rationale)
    assert "**Verdict: ACCEPT**" in report and "`used_ram_mib`" in report


def test_cli_collect_and_compare(tmp_path):
    base = tmp_path / "b.json"
    cand = tmp_path / "c.json"
    assert main(["collect", "--label", "baseline", "-o", str(base)]) == 0
    assert json.loads(base.read_text())["label"] == "baseline"
    base.write_text(json.dumps({"metrics": {"used_ram_mib": 1000}}))
    cand.write_text(json.dumps({"metrics": {"used_ram_mib": 900}}))
    out = tmp_path / "r.md"
    assert main(["compare", str(base), str(cand), "-o", str(out), "--strict"]) == 0
    assert "ACCEPT" in out.read_text()
    cand.write_text(json.dumps({"metrics": {"used_ram_mib": 1500}}))
    assert main(["compare", str(base), str(cand), "--strict"]) == 1
