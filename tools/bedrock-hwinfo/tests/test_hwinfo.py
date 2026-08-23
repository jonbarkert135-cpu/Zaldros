import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bedrock_hwinfo.hwinfo import (  # noqa: E402
    collect,
    collect_batteries,
    collect_disks,
    collect_displays,
    collect_network,
    parse_cpuinfo,
    parse_meminfo,
    parse_os_release,
    to_json,
    to_markdown,
)

CPUINFO = """processor\t: 0
vendor_id\t: GenuineIntel
model name\t: Intel(R) Core(TM) i7-1165G7 @ 2.80GHz
flags\t\t: fpu vme aes avx2 vmx sha_ni
processor\t: 1
vendor_id\t: GenuineIntel
model name\t: Intel(R) Core(TM) i7-1165G7 @ 2.80GHz
"""

MEMINFO = """MemTotal:       16269312 kB
MemFree:         1234567 kB
MemAvailable:    9876543 kB
SwapTotal:       8134656 kB
HugePages_Total:       0
"""


def write(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)


@pytest.fixture
def fake_sys(tmp_path):
    root = str(tmp_path / "sys")
    write(f"{root}/block/nvme0n1/size", "1000215216\n")
    write(f"{root}/block/nvme0n1/queue/rotational", "0\n")
    write(f"{root}/block/nvme0n1/removable", "0\n")
    write(f"{root}/block/nvme0n1/device/model", "Samsung SSD 980\n")
    write(f"{root}/block/sda/size", "3907029168\n")
    write(f"{root}/block/sda/queue/rotational", "1\n")
    write(f"{root}/block/loop0/size", "1024\n")  # must be skipped
    write(f"{root}/class/net/lo/address", "00:00:00:00:00:00\n")  # must be skipped
    write(f"{root}/class/net/wlan0/address", "aa:bb:cc:dd:ee:ff\n")
    write(f"{root}/class/net/wlan0/operstate", "up\n")
    write(f"{root}/class/net/wlan0/wireless/dummy", "x")
    write(f"{root}/class/net/eth0/address", "11:22:33:44:55:66\n")
    write(f"{root}/class/net/eth0/operstate", "down\n")
    write(f"{root}/class/net/eth0/speed", "1000\n")
    write(f"{root}/class/drm/card0/dummy", "x")  # skipped, no connector
    write(f"{root}/class/drm/card0-eDP-1/status", "connected\n")
    write(f"{root}/class/drm/card0-eDP-1/modes", "1920x1080\n1280x720\n")
    write(f"{root}/class/power_supply/AC/type", "Mains\n")  # skipped
    write(f"{root}/class/power_supply/BAT0/type", "Battery\n")
    write(f"{root}/class/power_supply/BAT0/capacity", "87\n")
    write(f"{root}/class/power_supply/BAT0/status", "Discharging\n")
    write(f"{root}/class/power_supply/BAT0/technology", "Li-ion\n")
    write(f"{root}/class/dmi/id/board_vendor", "LENOVO\n")
    write(f"{root}/class/dmi/id/product_name", "ThinkPad X1\n")
    return root


@pytest.fixture
def fake_proc(tmp_path):
    root = str(tmp_path / "proc")
    write(f"{root}/cpuinfo", CPUINFO)
    write(f"{root}/meminfo", MEMINFO)
    write(f"{root}/uptime", "36000.12 120000.00\n")
    return root


def test_parse_cpuinfo():
    cpu = parse_cpuinfo(CPUINFO)
    assert cpu.logical_cores == 2
    assert cpu.model.startswith("Intel(R) Core(TM) i7")
    assert cpu.vendor == "GenuineIntel"
    assert cpu.flags_of_interest == ["vmx", "aes", "avx2", "sha_ni"]


def test_parse_meminfo():
    memory = parse_meminfo(MEMINFO)
    assert memory.total_kb == 16269312
    assert memory.available_kb == 9876543
    assert memory.swap_total_kb == 8134656


def test_parse_os_release_handles_quotes():
    name, version = parse_os_release('NAME="Bedrock Linux"\nVERSION_ID="0.1"\n')
    assert (name, version) == ("Bedrock Linux", "0.1")


def test_disks_skip_virtual_and_convert_size(fake_sys):
    disks = {d.name: d for d in collect_disks(fake_sys)}
    assert set(disks) == {"nvme0n1", "sda"}  # loop0 excluded
    assert disks["nvme0n1"].size_bytes == 1000215216 * 512
    assert disks["nvme0n1"].rotational is False
    assert disks["nvme0n1"].model == "Samsung SSD 980"
    assert disks["sda"].rotational is True


def test_network_skips_loopback_and_detects_wireless(fake_sys):
    nics = {n.name: n for n in collect_network(fake_sys)}
    assert set(nics) == {"wlan0", "eth0"}
    assert nics["wlan0"].wireless is True
    assert nics["eth0"].wireless is False
    assert nics["eth0"].speed_mbps == 1000
    assert nics["wlan0"].state == "up"


def test_displays_only_connectors(fake_sys):
    displays = collect_displays(fake_sys)
    assert len(displays) == 1
    assert displays[0].connector == "eDP-1"
    assert displays[0].status == "connected"
    assert displays[0].modes == 2


def test_batteries_only_battery_type(fake_sys):
    batteries = collect_batteries(fake_sys)
    assert [b.name for b in batteries] == ["BAT0"]
    assert batteries[0].capacity_percent == 87
    assert batteries[0].status == "Discharging"


def test_missing_sources_yield_unknown_not_fabricated(tmp_path):
    empty = str(tmp_path / "nothing")
    inventory = collect(empty, empty)
    assert inventory.cpu.model is None
    assert inventory.memory.total_kb is None
    assert inventory.disks == []
    report = to_markdown(inventory)
    assert "unknown" in report
    # honesty rule: no invented vendor strings anywhere
    assert "Intel" not in report and "Microsoft" not in report


def test_full_collect_and_reports(fake_sys, fake_proc):
    inventory = collect(fake_sys, fake_proc)
    assert inventory.cpu.logical_cores == 2
    assert inventory.system.board_vendor == "LENOVO"
    assert inventory.system.uptime_seconds == pytest.approx(36000.12)

    markdown = to_markdown(inventory)
    assert "# Bedrock Linux — system & device inventory" in markdown
    assert "`nvme0n1`" in markdown and "SSD/NVMe" in markdown
    assert "BAT0: 87%" in markdown
    assert "15.5 GiB" in markdown  # 16269312 kB total memory

    data = json.loads(to_json(inventory))
    assert data["system"]["product_name"] == "ThinkPad X1"
    assert len(data["network"]) == 2
