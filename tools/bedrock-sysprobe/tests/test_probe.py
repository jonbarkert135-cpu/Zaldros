import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bedrock_sysprobe.probe import (  # noqa: E402
    ServiceInfo,
    parse_blame,
    parse_dep_list,
    parse_show,
    read_cpu_seconds,
    read_pss_kb,
    to_dicts,
    to_json,
    to_markdown,
)

SHOW_SAMPLE = """Description=Network Manager
ActiveState=active
SubState=running
UnitFileState=enabled
MainPID=812
CPUUsageNSec=4500000000
WantedBy=multi-user.target
RequiredBy=NetworkManager-wait-online.service
PartOf=
"""

BLAME_SAMPLE = """
         2.104s NetworkManager.service
          812ms systemd-udevd.service
           45ms dbus-broker.service
      1min 2.5s slow-thing.service
"""


def test_parse_show_reads_key_values():
    props = parse_show(SHOW_SAMPLE)
    assert props["Description"] == "Network Manager"
    assert props["MainPID"] == "812"
    assert props["PartOf"] == ""


def test_parse_show_ignores_garbage_lines():
    assert parse_show("no separator here\nA=1") == {"A": "1"}


def test_parse_blame_units_and_scales():
    blame = parse_blame(BLAME_SAMPLE)
    assert blame["NetworkManager.service"] == 2104.0
    assert blame["systemd-udevd.service"] == 812.0
    assert blame["dbus-broker.service"] == 45.0
    assert blame["slow-thing.service"] == 62500.0


def test_parse_dep_list_handles_empty():
    assert parse_dep_list("") == []
    assert parse_dep_list("a.target  b.target") == ["a.target", "b.target"]


def test_read_cpu_seconds():
    assert read_cpu_seconds({"CPUUsageNSec": "4500000000"}) == 4.5
    assert read_cpu_seconds({}) == 0.0
    assert read_cpu_seconds({"CPUUsageNSec": "[not set]"}) == 0.0


def test_read_pss_kb(tmp_path):
    proc = tmp_path / "42"
    proc.mkdir()
    (proc / "smaps_rollup").write_text("Rss:  2048 kB\nPss:  1024 kB\nPss_Dirty: 900 kB\n")
    assert read_pss_kb([42], proc_root=str(tmp_path)) == 1024
    # missing pid must not raise
    assert read_pss_kb([43], proc_root=str(tmp_path)) == 0


def _service(**kwargs) -> ServiceInfo:
    base = dict(
        unit="NetworkManager.service",
        description="Network Manager",
        active_state="active",
        sub_state="running",
        unit_file_state="enabled",
        main_pid=812,
        ram_kb=20480,
        cpu_seconds=4.5,
        boot_activation_ms=2104.0,
        wanted_by=["multi-user.target"],
        required_by=["NetworkManager-wait-online.service"],
    )
    base.update(kwargs)
    return ServiceInfo(**base)


def test_dependants_are_deduplicated_and_sorted():
    service = _service(wanted_by=["b.target", "a.target"], required_by=["a.target"], part_of=[])
    assert service.dependants == ["a.target", "b.target"]


def test_can_disable_false_when_required_or_static():
    assert _service().can_disable is False  # something requires it
    assert _service(required_by=[]).can_disable is True
    assert _service(required_by=[], unit_file_state="static").can_disable is False
    assert _service(required_by=[], unit_file_state="masked").can_disable is False


def test_markdown_report_contains_unit_and_totals():
    report = to_markdown([_service(), _service(unit="idle.service", ram_kb=0, required_by=[])])
    assert "# Bedrock Linux — service / dependency map" in report
    assert "`NetworkManager.service`" in report
    assert "Services inspected: **2**" in report
    assert "20.0" in report  # 20480 kB -> MB
    # highest memory consumer is listed first
    assert report.index("NetworkManager.service") < report.index("idle.service")


def test_json_report_is_valid_and_enriched():
    import json

    data = json.loads(to_json([_service()]))
    row = data["services"][0]
    assert row["unit"] == "NetworkManager.service"
    assert row["can_disable"] is False
    assert row["dependants"] == ["NetworkManager-wait-online.service", "multi-user.target"]


def test_to_dicts_matches_input_length():
    assert len(to_dicts([_service(), _service(unit="x.service")])) == 2
