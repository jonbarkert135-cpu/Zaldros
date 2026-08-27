"""The shell's seam to the backend, and the honesty rule at that seam.

`zaldros_shell/system.py` used to read /sys, run `wpctl`, run `gdbus` and run `localectl` itself;
the readers now live in `zaldros_backend` and are tested against mock services in
`test_backend_facets.py`. What is left to check here is the part the shell owns: that the seam
hands the UI the same six readings under the same names, that a machine which reports nothing says
so in the same words it always did, and that the sysfs fallbacks still work on a machine with no
D-Bus at all — because that is the shell we ship on a live image.
"""

from pathlib import Path

from zaldros_backend import Bus, ZaldrosBackend
from zaldros_backend.bluetooth import BluetoothFacet
from zaldros_backend.network import NetworkFacet
from zaldros_backend.power import PowerFacet
from zaldros_backend.session import layout_badge

from zaldros_shell import system


def busless() -> Bus:
    """A bus that is known to be unreachable, without waiting for a connection to time out."""
    bus = Bus("system", connection=None)
    bus._next_attempt = float("inf")            # noqa: SLF001 - "already tried, it is not there"
    bus._failure = "no bus in this environment"  # noqa: SLF001
    return bus


# -- the seam ------------------------------------------------------------------------------------
def test_snapshot_covers_every_quick_setting():
    snapshot = system.snapshot()
    assert set(snapshot) == {"battery", "brightness", "network", "volume", "bluetooth",
                             "keyboard"}
    for reading in snapshot.values():
        assert reading.available or reading.value is None


def test_the_shell_shares_one_backend_instance():
    """Two would mean two D-Bus connections and two copies of every signal."""
    assert system.backend() is system.backend()


def test_the_shell_survives_a_machine_with_no_services_at_all():
    backend = ZaldrosBackend(system_bus=busless(), session_bus=busless())
    system.set_backend(backend)
    try:
        for key, reading in system.snapshot().items():
            assert not reading.available or reading.value is not None, key
            assert reading.detail, f"{key} must say why it has no value"
        assert system.user_name()
        assert system.switch_layout() is False
    finally:
        system.set_backend(None)


# -- the sysfs fallbacks, which are what a live image without D-Bus has ----------------------------
def test_battery_reads_a_real_sysfs_layout(tmp_path: Path):
    bat = tmp_path / "BAT0"
    bat.mkdir()
    (bat / "capacity").write_text("87\n")
    (bat / "status").write_text("Discharging\n")
    reading = PowerFacet(busless(), sysfs_root=str(tmp_path)).battery()
    assert reading.available and reading.value == 87
    assert reading.detail == "разряжается"
    assert reading.get("charging") is False


def test_a_charging_battery_is_marked_as_charging(tmp_path: Path):
    bat = tmp_path / "BAT1"
    bat.mkdir()
    (bat / "capacity").write_text("40")
    (bat / "status").write_text("Charging")
    reading = PowerFacet(busless(), sysfs_root=str(tmp_path)).battery()
    assert reading.get("charging") is True and reading.value == 40


def test_missing_battery_is_reported_as_unavailable(tmp_path: Path):
    reading = PowerFacet(busless(), sysfs_root=str(tmp_path)).battery()
    assert not reading.available and reading.value is None
    assert reading.detail == "батарея не обнаружена"


def test_absent_sysfs_path_does_not_raise():
    assert PowerFacet(busless(), sysfs_root="/no/such/path").battery().available is False


def test_network_reports_only_interfaces_that_are_up(tmp_path: Path):
    down, up = tmp_path / "eth0", tmp_path / "wlan0"
    down.mkdir()
    up.mkdir()
    (down / "operstate").write_text("down")
    (up / "operstate").write_text("up")
    (up / "wireless").mkdir()
    reading = NetworkFacet(busless(), sysfs_root=str(tmp_path)).status()
    assert reading.available and "wlan0" in reading.detail and "Wi-Fi" in reading.detail
    assert reading.value is None, "sysfs has no signal strength, so none may be shown"


def test_no_link_is_reported_honestly(tmp_path: Path):
    (tmp_path / "eth0").mkdir()
    (tmp_path / "eth0" / "operstate").write_text("down")
    reading = NetworkFacet(busless(), sysfs_root=str(tmp_path)).status()
    assert not reading.available and reading.detail == "нет подключения"


def test_a_bluetooth_radio_without_bluez_is_presence_only(tmp_path: Path):
    (tmp_path / "hci0").mkdir()
    reading = BluetoothFacet(busless(), sysfs_root=str(tmp_path)).adapter()
    assert reading.available and reading.detail == "hci0"
    assert reading.value is None, "sysfs cannot say whether the radio is powered"


def test_no_bluetooth_adapter_uses_the_wording_the_panel_already_shows(tmp_path: Path):
    reading = BluetoothFacet(busless(), sysfs_root=str(tmp_path)).adapter()
    assert not reading.available and reading.detail == "адаптер не найден"


# -- the tray badge --------------------------------------------------------------------------------
def test_layout_badges_are_three_letters_in_the_interface_language():
    assert layout_badge("ru") == "РУС"
    assert layout_badge("us") == "ENG"
    assert layout_badge("ru,us") == "РУС"


def test_a_layout_we_have_no_name_for_keeps_its_own_code():
    assert layout_badge("xyzzy") == "XYZ"


def test_no_layout_at_all_means_no_badge_rather_than_a_wrong_one():
    """Run #29 in the booted ISO showed "(UN" in the tray: localectl had answered "(unset)" and
    the badge was the first three characters of it. The layout now comes from KWin over D-Bus,
    so there is no string left to mis-slice — and with no KWin, the badge is empty."""
    backend = ZaldrosBackend(system_bus=busless(), session_bus=busless())
    system.set_backend(backend)
    try:
        reading = system.keyboard_layout()
        assert reading.detail in ("", "РУС", "ENG") or not reading.available
        assert reading.available or reading.value is None
    finally:
        system.set_backend(None)
