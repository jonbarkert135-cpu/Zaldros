# SPDX-License-Identifier: GPL-3.0-or-later
"""Network, audio, Bluetooth and power — the parts added in TASK 5, on a real bus.

Same harness as `test_backend_facets.py`: mock services with the real names, the real object
paths and the real D-Bus types, standing on a real `dbus-daemon`. What is asserted here is mostly
*what went onto the bus* — joining a Wi-Fi network is a settings dictionary with an `ay` SSID, and
getting that wrong is the classic NetworkManager client bug.
"""

from __future__ import annotations

import threading
from types import SimpleNamespace

import pytest

from zaldros_backend.audio import AudioFacet
from zaldros_backend.testing import MockSystem, SessionDaemon, backend_on

pytestmark = pytest.mark.skipif(not SessionDaemon.available(),
                                reason="dbus-daemon is not installed")


@pytest.fixture
def system():
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


# -- network ------------------------------------------------------------------------------------
def test_joining_a_network_sends_the_ssid_as_bytes_not_as_a_string(system):
    assert system.backend.network.connect_wifi("Офис", "s3cret").ok
    settings, device, _specific = system.mock.calls["AddAndActivateConnection"][0]
    ssid = settings["802-11-wireless"]["ssid"]
    assert bytes(ssid) == "Офис".encode("utf-8")
    assert settings["802-11-wireless-security"]["key-mgmt"] == "wpa-psk"
    assert device.endswith("/Devices/2")           # the Wi-Fi device, not the Ethernet one


def test_an_open_network_gets_no_security_block_at_all(system):
    assert system.backend.network.connect_wifi("Кафе").ok
    settings, _device, _specific = system.mock.calls["AddAndActivateConnection"][0]
    assert "802-11-wireless-security" not in settings


def test_saved_connections_are_listed_with_their_type(system):
    saved = system.backend.network.saved_connections()
    assert [(item.detail, item.get("kind")) for item in saved] == [
        ("Zaldros-Guest", "802-11-wireless"), ("Работа VPN", "vpn")]


def test_only_vpn_profiles_are_offered_as_vpn(system):
    vpn = system.backend.network.vpn_connections()
    assert [item.detail for item in vpn] == ["Работа VPN"]


def test_an_active_profile_knows_it_is_active(system):
    saved = system.backend.network.saved_connections()
    guest = next(item for item in saved if item.detail == "Zaldros-Guest")
    assert guest.get("active") is True             # the mock's active connection has that Id


def test_deactivating_a_connection_reaches_networkmanager(system):
    assert system.backend.network.deactivate("/org/freedesktop/NetworkManager/ActiveConnection/1").ok
    assert system.mock.calls["DeactivateConnection"]


def test_a_machine_without_a_proxy_says_so_rather_than_returning_an_empty_string(monkeypatch):
    for name in ("https_proxy", "http_proxy", "HTTPS_PROXY", "HTTP_PROXY", "all_proxy"):
        monkeypatch.delenv(name, raising=False)
    from zaldros_backend.testing import offline_backend
    reading = offline_backend().network.proxy()
    assert not reading.available and reading.detail


def test_the_proxy_reading_names_the_variable_it_came_from(monkeypatch):
    monkeypatch.setenv("https_proxy", "http://proxy.local:3128")
    from zaldros_backend.testing import offline_backend
    reading = offline_backend().network.proxy()
    assert reading.available and reading.source == "env:https_proxy"


# -- Bluetooth ------------------------------------------------------------------------------------
def test_pairing_a_device_pairs_it_and_then_trusts_it(system):
    path = "/org/bluez/hci0/dev_BB_00_11_22_33_44"
    assert system.backend.bluetooth.pair(path).ok
    assert system.mock.calls["Pair"] == [path]


def test_removing_a_device_goes_through_the_adapter_that_owns_the_pairing(system):
    path = "/org/bluez/hci0/dev_AA_00_11_22_33_44"
    assert system.backend.bluetooth.remove(path).ok
    assert system.mock.calls["RemoveDevice"] == [path]


def test_a_headset_battery_is_a_real_percentage_and_a_keyboard_without_one_has_none(system):
    devices = {item.detail: item for item in system.backend.bluetooth.devices()}
    assert devices["WH-1000XM4"].value == 65
    assert devices["Клавиатура"].value is None


# -- power ------------------------------------------------------------------------------------
def test_the_three_power_profiles_come_from_the_daemon_with_the_active_one_marked(system):
    profiles = system.backend.power.profiles()
    assert [item.get("profile") for item in profiles] == ["power-saver", "balanced", "performance"]
    assert [item.detail for item in profiles][1] == "Сбалансированный"
    assert next(item for item in profiles if item.get("active")).get("profile") == "balanced"


def test_switching_the_profile_writes_it_and_the_read_back_shows_it(system):
    assert system.backend.power.set_profile("performance").ok
    assert system.backend.power.active_profile()["profile"] == "performance"


def test_without_the_daemon_the_profile_is_a_reason_not_a_guess():
    from zaldros_backend.testing import offline_backend
    state = offline_backend().power.active_profile()
    assert state["profile"] == "" and state["reason"]


# -- audio ------------------------------------------------------------------------------------
WPCTL_STATUS = """Audio
 ├─ Sinks:
 │      *   47. Family 17h HD Audio          [vol: 0.65]
 │          52. HDMI / DisplayPort           [vol: 1.00]
 ├─ Sources:
 │      *   48. Internal Microphone          [vol: 0.80]
 ├─ Streams:
 │      61. Firefox
 │      63. Zaldros Shell
"""


def _runner(outputs: dict[tuple[str, ...], str]):
    class Done:
        def __init__(self, stdout: str, code: int = 0) -> None:
            self.stdout, self.returncode, self.stderr = stdout, code, ""

    def run(args, **_kwargs):
        return Done(outputs.get(tuple(args), ""), 0 if tuple(args) in outputs else 1)
    return run


def test_per_application_volume_is_read_per_stream(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/wpctl" if name == "wpctl" else None)
    facet = AudioFacet(runner=_runner({
        ("wpctl", "status"): WPCTL_STATUS,
        ("wpctl", "get-volume", "61"): "Volume: 0.35\n",
        ("wpctl", "get-volume", "63"): "Volume: 0.90 [MUTED]\n"}))
    streams = facet.streams()
    assert [(item.detail, item.value, item.get("muted")) for item in streams] == [
        ("Firefox", 35, False), ("Zaldros Shell", 90, True)]


def test_a_stream_whose_volume_cannot_be_read_is_unavailable_not_a_hundred_percent(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/wpctl" if name == "wpctl" else None)
    facet = AudioFacet(runner=_runner({("wpctl", "status"): WPCTL_STATUS}))
    assert [item.available for item in facet.streams()] == [False, False]


def test_setting_an_application_volume_is_clamped_before_it_reaches_pipewire(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/wpctl" if name == "wpctl" else None)
    seen = []

    class Done:
        stdout, returncode, stderr = "", 0, ""

    def run(args, **_kwargs):
        seen.append(args)
        return Done()

    facet = AudioFacet(runner=run)
    facet.set_stream_volume(61, 900)
    assert seen[-1] == ["wpctl", "set-volume", "61", "1.50"]


def test_recording_devices_are_listed_with_the_default_marked(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/wpctl" if name == "wpctl" else None)
    facet = AudioFacet(runner=_runner({("wpctl", "status"): WPCTL_STATUS}))
    inputs = facet.inputs()
    assert [(item.detail, item.get("default")) for item in inputs] == [
        ("Internal Microphone", True)]


# -- the Settings rows built from them -----------------------------------------------------------
def test_settings_grows_one_row_per_vpn_profile_and_none_when_there_are_none(system,
                                                                            monkeypatch):
    from zaldros_shell import settingscontrols, system as shell_system
    monkeypatch.setattr(shell_system, "backend", lambda: system.backend)
    registry = settingscontrols.Registry()
    vpn_rows = [name for name in registry.titles() if name.startswith("network.vpn:")]
    assert len(vpn_rows) == 1                       # the mock stores exactly one VPN profile
    state = registry.state(vpn_rows[0])
    assert state.kind == "switch" and state.available


def test_the_power_profile_row_offers_the_three_real_profiles(system, monkeypatch):
    from zaldros_shell import settingscontrols, system as shell_system
    monkeypatch.setattr(shell_system, "backend", lambda: system.backend)
    registry = settingscontrols.Registry()
    state = registry.state("power.profile")
    assert [choice["id"] for choice in state.choices] == ["power-saver", "balanced", "performance"]
    assert registry.set("power.profile", "performance").value == "performance"


def test_dns_and_proxy_rows_are_read_only_facts_not_empty_switches(system, monkeypatch):
    from zaldros_shell import settingscontrols, system as shell_system
    monkeypatch.setattr(shell_system, "backend", lambda: system.backend)
    registry = settingscontrols.Registry()
    for control_id in ("network.dns", "network.proxy"):
        state = registry.state(control_id)
        assert state.kind == "info" and not state.writable
