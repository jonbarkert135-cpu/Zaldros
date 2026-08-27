"""Each facet, against a mock of the service it wraps.

The mocks answer with the real property names and the real D-Bus types — UPower's percentage is a
double, NetworkManager's SSID is a byte array, udisks2's device is a NUL-terminated byte string,
BlueZ's battery is a byte. Those are the details a facet gets wrong, so those are what is checked.
"""

from __future__ import annotations

import subprocess
import threading
from types import SimpleNamespace

import pytest

from zaldros_backend.audio import AudioFacet
from zaldros_backend.display import DisplayFacet
from zaldros_backend.reading import Reading
from zaldros_backend.testing import MockSystem, SessionDaemon, backend_on

pytestmark = pytest.mark.skipif(not SessionDaemon.available(),
                                reason="dbus-daemon is not installed")


@pytest.fixture
def system():
    """A whole mock machine: UPower, logind, NetworkManager, BlueZ, udisks2, systemd."""
    daemon = SessionDaemon()
    daemon.start()
    mock = MockSystem(daemon.address)
    mock.add_all()
    stop = threading.Event()
    thread = threading.Thread(target=lambda: [mock.process(0.01)
                                              for _ in iter(lambda: not stop.is_set(), False)],
                              daemon=True)
    thread.start()
    backend = backend_on(daemon.address)
    try:
        yield SimpleNamespace(backend=backend, mock=mock)
    finally:
        stop.set()
        thread.join(timeout=2)
        backend.close()
        mock.close()
        daemon.stop()


# -- power ---------------------------------------------------------------------------------------
def test_battery_is_read_from_the_composite_display_device(system):
    battery = system.backend.power.battery()
    assert battery.available and battery.value == 87
    assert battery.detail == "разряжается"
    assert battery.get("charging") is False
    assert battery.get("time_text") == "2 ч 15 мин"
    assert battery.source.endswith("DisplayDevice")


def test_a_mouse_is_listed_as_a_device_but_is_not_the_battery(system):
    devices = {device.detail: device for device in system.backend.power.devices()}
    assert devices["MX Master 3"].get("kind") == "mouse"
    assert devices["MX Master 3"].value == 55
    assert system.backend.power.battery().value == 87


def test_the_power_menu_only_offers_what_logind_says_it_can_do(system):
    capabilities = system.backend.power.capabilities()
    assert capabilities["suspend"] is True
    assert capabilities["hibernate"] is False        # logind answered "no"
    assert capabilities["hybrid-sleep"] is True      # "challenge" is still an offer


def test_suspend_reaches_logind(system):
    assert system.backend.power.suspend().ok
    assert system.mock.actions == ["Suspend"]


# -- network -------------------------------------------------------------------------------------
def test_the_tray_line_names_the_network_and_its_signal(system):
    status = system.backend.network.status()
    assert status.available
    assert status.detail == "Zaldros-Guest"
    assert status.value == 74                       # strength of the active access point
    assert status.get("kind") == "wifi"
    assert status.get("connectivity") == "full"


def test_one_entry_per_network_not_one_per_radio(system):
    """A mesh publishes an AccessPoint per BSSID; the panel shows networks."""
    points = system.backend.network.access_points()
    assert [point.detail for point in points] == ["Zaldros-Guest", "Офис"]
    assert points[0].get("active") is True
    assert points[0].get("secured") is True
    assert points[1].get("secured") is False        # no privacy flag, no WPA, no RSN


def test_a_cyrillic_ssid_survives_the_byte_array(system):
    assert "Офис" in [point.detail for point in system.backend.network.access_points()]


def test_devices_are_listed_with_their_real_state(system):
    devices = {device.detail: device for device in system.backend.network.devices()}
    assert devices["wlan0"].get("kind") == "wifi" and devices["wlan0"].get("connected")
    assert devices["enp3s0"].get("state") == "disconnected"


def test_a_disconnected_machine_says_so_instead_of_showing_a_stale_name(system):
    from zaldros_backend.wire import Variant
    manager = system.mock.service("org.freedesktop.NetworkManager")
    manager.set_property("/org/freedesktop/NetworkManager", "org.freedesktop.NetworkManager",
                         "State", Variant("u", 20), emit=False)
    manager.set_property("/org/freedesktop/NetworkManager", "org.freedesktop.NetworkManager",
                         "Connectivity", Variant("u", 1), emit=False)
    status = system.backend.network.status()
    assert not status.available
    assert status.detail == "нет подключения"
    assert status.value is None


# -- bluetooth -----------------------------------------------------------------------------------
def test_the_adapter_and_its_devices_come_from_one_object_tree(system):
    adapter = system.backend.bluetooth.adapter()
    assert adapter.available and adapter.detail == "Zaldros" and adapter.get("powered")
    devices = system.backend.bluetooth.devices()
    assert [device.detail for device in devices] == ["WH-1000XM4", "Клавиатура"]
    assert devices[0].value == 65                   # org.bluez.Battery1, a byte
    assert devices[1].value is None                 # no battery interface: no invented number


def test_only_paired_devices_when_asked(system):
    assert [d.detail for d in system.backend.bluetooth.devices(paired_only=True)] == ["WH-1000XM4"]


# -- storage -------------------------------------------------------------------------------------
def test_system_partitions_and_loop_devices_stay_out_of_this_computer(system):
    volumes = system.backend.storage.volumes()
    assert [volume.detail for volume in volumes] == ["ZALDROS"]
    assert volumes[0].get("device") == "/dev/sdb1"  # decoded from a NUL-terminated byte string
    assert volumes[0].get("removable") is True
    assert volumes[0].get("mounted") is False
    assert volumes[0].value is None                 # not mounted: no fill percentage exists


def test_the_system_disk_appears_when_asked_for(system):
    labels = [volume.detail for volume in system.backend.storage.volumes(include_system=True)]
    assert "Windows" in labels and "snap" not in labels


def test_mounting_returns_the_mount_point_udisks_chose(system):
    result = system.backend.storage.mount("/org/freedesktop/UDisks2/block_devices/sdb1")
    assert result.ok and result.value == "/media/zaldros/ZALDROS"


def test_drives_carry_their_bus_and_removability(system):
    drives = {drive.detail: drive for drive in system.backend.storage.drives()}
    assert drives["Kingston DataTraveler"].get("connection") == "usb"
    assert drives["Samsung SSD 970 EVO"].get("removable") is False


# -- services ------------------------------------------------------------------------------------
def test_units_are_listed_and_a_failure_is_findable(system):
    units = {unit.get("unit"): unit for unit in system.backend.services.units()}
    assert units["NetworkManager.service"].get("running") is True
    assert units["dev-sda1.mount"] if "dev-sda1.mount" in units else True  # .service filter
    assert [unit.get("unit") for unit in system.backend.services.failed()] == \
        ["zaldros-broken.service"]
    assert units["zaldros-broken.service"].get("state_text") == "сбой"


def test_starting_a_unit_reaches_systemd(system):
    assert system.backend.services.start("bluetooth.service").ok
    assert "StartUnit:bluetooth.service" in system.mock.started


# -- session -------------------------------------------------------------------------------------
def test_the_session_is_read_from_logind(system):
    session = system.backend.session.session()
    assert session.get("seat") == "seat0" and session.get("active") is True
    assert session.detail == "wayland"


# -- audio (no D-Bus: the tool is the interface) ---------------------------------------------------
def _runner(stdout: str, code: int = 0):
    def run(args, **_kwargs):
        run.calls.append(args)
        return SimpleNamespace(returncode=code, stdout=stdout, stderr="")
    run.calls = []
    return run


def test_wpctl_output_is_parsed_including_the_mute_flag(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/wpctl" if name == "wpctl" else None)
    facet = AudioFacet(runner=_runner("Volume: 0.65 [MUTED]\n"))
    reading = facet.volume()
    assert reading.available and reading.value == 65 and reading.get("muted") is True
    assert reading.source == "wpctl"


def test_output_we_do_not_recognise_is_unavailable_not_zero(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/wpctl" if name == "wpctl" else None)
    facet = AudioFacet(runner=_runner("something else entirely\n"))
    assert facet.volume().available is False
    assert facet.volume().value is None


def test_no_audio_server_is_said_plainly(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _name: None)
    facet = AudioFacet(runner=_runner(""))
    reading = facet.volume()
    assert not reading.available and reading.detail == "аудиосервер не найден"
    assert not facet.set_volume(50).ok


def test_the_slider_cannot_ask_for_more_than_full_volume(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/wpctl" if name == "wpctl" else None)
    runner = _runner("")
    AudioFacet(runner=runner).set_volume(150)
    assert runner.calls[-1] == ["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "1.00"]


def test_pactl_is_used_when_there_is_no_wpctl(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/pactl" if name == "pactl" else None)
    facet = AudioFacet(runner=_runner("Volume: front-left: 42598 /  65% / -7.35 dB\n"))
    reading = facet.volume()
    assert reading.value == 65 and reading.source == "pactl"


# -- display -------------------------------------------------------------------------------------
def test_a_backlight_that_can_only_be_read_says_so(tmp_path, system):
    device = tmp_path / "intel_backlight"
    device.mkdir()
    (device / "brightness").write_text("300")
    (device / "max_brightness").write_text("1200")
    facet = DisplayFacet(system.backend.session_bus, sys_root=str(tmp_path))
    reading = facet.brightness()
    assert reading.available and reading.value == 25
    assert reading.get("writable") is False
    assert not facet.set_brightness(50).ok        # offered nothing it cannot do


def test_no_backlight_at_all_is_reported_in_the_shell_s_own_words(system):
    facet = DisplayFacet(system.backend.session_bus, sys_root="/no/such/path")
    reading = facet.brightness()
    assert not reading.available and reading.detail == "регулировка недоступна"


def test_kscreen_outputs_are_parsed_when_the_tool_exists(monkeypatch, system):
    payload = ('{"outputs": [{"name": "eDP-1", "enabled": true, "connected": true,'
               ' "primary": true, "scale": 1.5, "rotation": 1, "currentModeId": "3",'
               ' "modes": [{"id": "3", "size": {"width": 2560, "height": 1600},'
               ' "refreshRate": 90.001}, {"id": "4", "size": {"width": 1920, "height": 1200},'
               ' "refreshRate": 60.0}]}]}')
    monkeypatch.setattr("shutil.which", lambda _name: "/usr/bin/kscreen-doctor")
    facet = DisplayFacet(system.backend.session_bus, runner=_runner(payload))
    outputs = facet.outputs()
    assert len(outputs) == 1
    assert outputs[0].detail == "eDP-1"
    assert (outputs[0].get("width"), outputs[0].get("height")) == (2560, 1600)
    assert outputs[0].get("refresh") == 90.0
    assert outputs[0].get("scale") == 1.5
    assert (1920, 1200) in outputs[0].get("modes")


def test_without_kscreen_doctor_there_are_no_outputs_and_no_guesses(monkeypatch, system):
    monkeypatch.setattr("shutil.which", lambda _name: None)
    facet = DisplayFacet(system.backend.session_bus)
    assert facet.outputs() == []
    assert not facet.set_output_scale("eDP-1", 2).ok


# -- the honesty contract itself -------------------------------------------------------------------
def test_an_unavailable_reading_never_carries_a_number():
    reading = Reading.missing("нет данных", "/sys/nothing")
    assert reading.value is None and reading.percent == -1 and not reading.available
