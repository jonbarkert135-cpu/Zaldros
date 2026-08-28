# SPDX-License-Identifier: GPL-3.0-or-later
"""The Device Manager against a synthetic sysfs, and against this machine's real one.

A container has almost no sysfs, which makes it the perfect test of the honesty rules: every
category must explain its emptiness instead of quietly showing nothing.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from zaldros_backend import devices


def make_pci(root: Path, address: str, klass: str, vendor: str, device: str,
             driver: str | None) -> None:
    entry = root / "bus" / "pci" / "devices" / address
    entry.mkdir(parents=True)
    (entry / "class").write_text(klass)
    (entry / "vendor").write_text(vendor)
    (entry / "device").write_text(device)
    (entry / "revision").write_text("0x01")
    if driver:
        target = root / "drivers" / driver
        target.mkdir(parents=True, exist_ok=True)
        (entry / "driver").symlink_to(target)


@pytest.fixture()
def sysfs(tmp_path: Path) -> Path:
    root = tmp_path / "sys"
    make_pci(root, "0000:00:02.0", "0x030000", "0x8086", "0x9a49", "i915")
    make_pci(root, "0000:00:1f.3", "0x040300", "0x8086", "0xa0c8", None)
    net = root / "class" / "net" / "wlan0"
    net.mkdir(parents=True)
    (net / "address").write_text("aa:bb:cc:dd:ee:ff")
    (net / "operstate").write_text("up")
    (net / "mtu").write_text("1500")
    driver = root / "drivers" / "iwlwifi"
    driver.mkdir(parents=True, exist_ok=True)
    (net / "device").mkdir()
    (net / "device" / "driver").symlink_to(driver)
    (root / "class" / "net" / "lo").mkdir(parents=True)
    disk = root / "class" / "block" / "nvme0n1"
    disk.mkdir(parents=True)
    (disk / "size").write_text("1000215216")
    (disk / "queue").mkdir()
    (disk / "queue" / "rotational").write_text("0")
    (disk / "device").mkdir()
    (disk / "device" / "model").write_text("SAMSUNG MZVL2512")
    part = root / "class" / "block" / "nvme0n1p1"
    part.mkdir(parents=True)
    (part / "partition").write_text("1")
    (root / "class" / "block" / "loop0").mkdir(parents=True)
    (disk / "device" / "driver").symlink_to(root / "drivers" / "iwlwifi")
    return root


def facet(sysfs: Path, proc: str = "/proc") -> devices.DevicesFacet:
    return devices.DevicesFacet(str(sysfs), proc)


# --- enumeration -------------------------------------------------------------------------------
def test_a_pci_device_lands_in_the_windows_category_for_its_class(sysfs: Path):
    found = devices.pci_devices(str(sysfs / "bus" / "pci" / "devices"))
    assert {device.category for device in found} == {"Видеоадаптеры",
                                                     "Звук, видео и игровые устройства"}


def test_a_device_without_a_bound_driver_is_marked_broken_not_hidden(sysfs: Path):
    found = devices.pci_devices(str(sysfs / "bus" / "pci" / "devices"))
    audio = next(device for device in found
                 if device.category == "Звук, видео и игровые устройства")
    assert not audio.working and audio.problem == devices.NO_DRIVER
    graphics = next(device for device in found if device.category == "Видеоадаптеры")
    assert graphics.working and graphics.driver == "i915"


def test_an_unknown_vendor_keeps_its_ids_instead_of_getting_an_invented_name(tmp_path: Path):
    make_pci(tmp_path, "0000:00:05.0", "0x030000", "0xdead", "0xbeef", None)
    found = devices.pci_devices(str(tmp_path / "bus" / "pci" / "devices"))
    assert found[0].name == "устройство PCI [dead:beef]"


def test_loopback_is_not_a_network_adapter(sysfs: Path):
    names = [device.name for device in devices.network_devices(str(sysfs / "class"))]
    assert names == ["wlan0"]


def test_a_partition_is_not_a_disk_and_neither_is_a_loop_device(sysfs: Path):
    disks = devices.block_devices(str(sysfs / "class"))
    assert [device.name for device in disks] == ["SAMSUNG MZVL2512"]
    assert disks[0].details["Тип"] == "SSD/NVMe"


def test_usb_interfaces_and_root_hubs_are_not_listed_as_devices(tmp_path: Path):
    root = tmp_path / "bus" / "usb" / "devices"
    for name in ("usb1", "1-2", "1-2:1.0"):
        (root / name).mkdir(parents=True)
    (root / "1-2" / "idVendor").write_text("046d")
    (root / "1-2" / "idProduct").write_text("c52b")
    (root / "1-2" / "product").write_text("Unifying Receiver")
    found = devices.usb_devices(str(root))
    assert [device.name for device in found] == ["Unifying Receiver"]


def test_only_connected_outputs_are_monitors(tmp_path: Path):
    for name, status in (("card0-HDMI-A-1", "connected"), ("card0-DP-1", "disconnected")):
        entry = tmp_path / name
        entry.mkdir()
        (entry / "status").write_text(status)
        (entry / "modes").write_text("1920x1080\n1280x720\n")
    found = devices.displays(str(tmp_path))
    assert [device.name for device in found] == ["HDMI-A-1"]
    assert found[0].details["Лучший режим"] == "1920x1080"


# --- the tree ----------------------------------------------------------------------------------
def test_every_empty_category_carries_a_reason_and_never_just_vanishes(tmp_path: Path):
    tree = devices.DevicesFacet(str(tmp_path / "empty"), "/proc").tree()
    empty = [node for node in tree if not node["devices"]]
    assert empty, "a machine with no sysfs must still show the categories"
    assert all(node["reason"] for node in empty)


def test_the_reason_names_the_path_the_kernel_did_not_show(tmp_path: Path):
    tree = devices.DevicesFacet(str(tmp_path / "empty"), "/proc").tree()
    graphics = next(node for node in tree if node["category"] == "Видеоадаптеры")
    assert "bus/pci/devices" in graphics["reason"]


def test_the_tree_counts_problems(sysfs: Path):
    counts = facet(sysfs).counts()
    assert counts["problems"] == 1


def test_rescanning_a_bus_that_is_not_there_says_so_instead_of_reporting_success(tmp_path: Path):
    result = devices.DevicesFacet(str(tmp_path), "/proc").rescan()
    assert not result.available and result.detail


def test_this_machine_reports_its_own_processor_and_memory():
    found = devices.DevicesFacet().devices()
    categories = {device.category for device in found}
    assert "Процессоры" in categories and "Оперативная память" in categories


# --- the Qt model --------------------------------------------------------------------------------
def test_categories_collapse_and_expand_and_a_broken_one_starts_open(sysfs: Path, qt_app):
    from zaldros_shell.model import DeviceModel
    model = DeviceModel(facet(sysfs))
    model.refresh()
    rows = [model.get(index) for index in range(model.count)]
    audio_row = next(row for row in rows
                     if row["kind"] == "device" and not row["working"])
    assert audio_row["category"] == "Звук, видео и игровые устройства"
    graphics_index = next(index for index, row in enumerate(rows)
                          if row["kind"] == "category" and row["category"] == "Видеоадаптеры")
    assert not rows[graphics_index]["expanded"]
    model.toggle(graphics_index)
    assert any(row["title"].startswith("Intel") for row in
               (model.get(index) for index in range(model.count)))


def test_the_model_summary_counts_devices_and_problems(sysfs: Path, qt_app):
    from zaldros_shell.model import DeviceModel
    model = DeviceModel(facet(sysfs))
    model.refresh()
    assert model.problemCount == 1
    assert "проблемами" in model.summary.lower()
