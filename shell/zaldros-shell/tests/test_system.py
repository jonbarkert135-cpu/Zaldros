"""Tests for the system readouts. The contract under test is the honesty rule: unknown values must
come back as unavailable, never as a plausible-looking number."""
from pathlib import Path

from zaldros_shell import system


def test_battery_reads_a_real_sysfs_layout(tmp_path: Path):
    bat = tmp_path / "BAT0"
    bat.mkdir()
    (bat / "capacity").write_text("87\n")
    (bat / "status").write_text("Discharging\n")
    reading = system.battery(str(tmp_path))
    assert reading.available and reading.value == 87 and reading.detail == "Discharging"


def test_missing_battery_is_reported_as_unavailable(tmp_path: Path):
    reading = system.battery(str(tmp_path))
    assert not reading.available and reading.value is None and reading.detail


def test_absent_sysfs_path_does_not_raise():
    assert system.battery("/no/such/path").available is False


def test_backlight_is_a_percentage_of_the_maximum(tmp_path: Path):
    device = tmp_path / "intel_backlight"
    device.mkdir()
    (device / "brightness").write_text("300")
    (device / "max_brightness").write_text("1200")
    assert system.backlight(str(tmp_path)).value == 25


def test_network_reports_only_interfaces_that_are_up(tmp_path: Path):
    down, up = tmp_path / "eth0", tmp_path / "wlan0"
    down.mkdir(); up.mkdir()
    (down / "operstate").write_text("down")
    (up / "operstate").write_text("up")
    (up / "wireless").mkdir()
    reading = system.network(str(tmp_path))
    assert reading.available and "wlan0" in reading.detail and "Wi-Fi" in reading.detail


def test_no_link_is_reported_honestly(tmp_path: Path):
    (tmp_path / "eth0").mkdir()
    (tmp_path / "eth0" / "operstate").write_text("down")
    assert system.network(str(tmp_path)).available is False


def test_volume_without_an_audio_server_is_unavailable_not_zero():
    reading = system.volume()
    assert reading.available or reading.value is None


def test_snapshot_covers_every_quick_setting():
    snapshot = system.snapshot()
    assert set(snapshot) == {"battery", "brightness", "network", "volume", "bluetooth"}
    for reading in snapshot.values():
        assert reading.available or reading.value is None
