"""The facets Settings writes through, against mocks of the services they wrap.

Every test here is a *round trip*: write, then read the state back from the mock service over the
real bus. A test that only asserts "the call was made" would pass for a facet that sends the wrong
property name to the right object, which is exactly the mistake this layer makes.
"""

from __future__ import annotations

import threading
from types import SimpleNamespace

import pytest

from zaldros_backend.defaultapps import DefaultAppsFacet
from zaldros_backend.firewall import FirewallFacet
from zaldros_backend.testing import MockSystem, SessionDaemon, backend_on, offline_backend

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


# -- time and language ---------------------------------------------------------------------------
def test_the_clock_is_read_with_its_ntp_state(system):
    clock = system.backend.localetime.clock()
    assert clock.available and clock.get("timezone") == "Europe/Moscow"
    assert clock.get("ntp") is True and clock.get("can_ntp") is True


def test_changing_the_timezone_changes_the_system_and_the_next_read_shows_it(system):
    assert system.backend.localetime.set_timezone("Asia/Jerusalem").ok
    assert system.backend.localetime.clock().get("timezone") == "Asia/Jerusalem"


def test_turning_ntp_off_is_visible_in_the_reading(system):
    assert system.backend.localetime.set_ntp(False).ok
    clock = system.backend.localetime.clock()
    assert clock.get("ntp") is False and clock.get("synchronized") is False


def test_the_language_is_the_lang_variable_and_only_that_is_written(system):
    assert system.backend.localetime.locale().get("lang") == "ru_RU.UTF-8"
    assert system.backend.localetime.set_language("de_DE.UTF-8").ok
    locale = system.backend.localetime.locale()
    assert locale.get("lang") == "de_DE.UTF-8"
    assert locale.get("variables") == {"LANG": "de_DE.UTF-8"}


def test_the_keyboard_default_goes_to_localed(system):
    assert system.backend.localetime.set_x11_keyboard("ru,us").ok
    assert system.backend.localetime.locale().get("x11_layout") == "ru,us"


# -- input devices -------------------------------------------------------------------------------
def test_devices_are_split_by_what_they_are(system):
    pointers = system.backend.input.devices("pointer")
    touchpads = system.backend.input.devices("touchpad")
    assert [device.detail for device in touchpads] == ["SynPS/2 Synaptics TouchPad"]
    assert len(pointers) == 2, "a touchpad is a pointer too, as libinput reports it"


def test_a_touchpad_switch_changes_the_device_and_reads_back(system):
    assert system.backend.input.set_for_kind("touchpad", "tap_to_click", True).ok
    assert system.backend.input.value_for_kind("touchpad", "tap_to_click").get("setting") is True


def test_pointer_speed_is_a_real_double_on_the_device(system):
    assert system.backend.input.set_for_kind("pointer", "acceleration", 0.5).ok
    assert system.backend.input.value_for_kind("pointer", "acceleration").get("setting") == 0.5


def test_an_option_the_hardware_does_not_have_is_refused_not_faked(system):
    """The mouse mock has no supportsDisableEvents: the switch must say so, not write anyway."""
    reading = system.backend.input.option("event3", "enabled")
    assert not reading.available
    assert not system.backend.input.set_option("event3", "enabled", False).ok


# -- accounts ------------------------------------------------------------------------------------
def test_users_are_listed_without_system_accounts(system):
    names = [user.get("name") for user in system.backend.accounts.users()]
    assert names == ["guest", "zaldros"] or names == ["zaldros", "guest"]


def test_automatic_login_round_trips(system):
    assert system.backend.accounts.automatic_login().get("enabled") is False
    assert system.backend.accounts.set_automatic_login("zaldros", True).ok
    state = system.backend.accounts.automatic_login()
    assert state.get("enabled") is True and state.get("user") == "zaldros"


def test_making_a_user_an_administrator_is_stored(system):
    assert system.backend.accounts.set_admin("guest", True).ok
    assert system.backend.accounts.user("guest").get("admin") is True


# -- privacy permissions --------------------------------------------------------------------------
def test_camera_permissions_are_read_per_application(system):
    camera = system.backend.permissions.device("camera")
    assert camera.get("allowed") == ["org.chromium.Chromium"]
    assert camera.get("denied") == ["im.riot.Riot"]
    assert camera.get("enabled") is False, "one denial means the page switch is off"


def test_denying_a_device_writes_every_application_and_reads_back(system):
    assert system.backend.permissions.set_device("microphone", False).ok
    microphone = system.backend.permissions.device("microphone")
    assert microphone.get("denied") == ["org.chromium.Chromium"]
    assert microphone.get("enabled") is False


def test_a_table_nobody_asked_about_cannot_be_written_blindly(system):
    result = system.backend.permissions.set_device("location", False)
    assert not result.ok and "asked" in result.error


# -- updates ---------------------------------------------------------------------------------------
def test_updates_are_counted_from_the_transaction_signals(system):
    reading = system.backend.updates.updates(timeout=10.0)
    assert reading.available and reading.value == 2
    assert reading.get("security") == 1
    assert "2 обновлений" in reading.detail


def test_refresh_waits_for_finished(system):
    assert system.backend.updates.refresh(timeout=10.0).ok


def test_without_packagekit_updates_are_unavailable_not_zero():
    backend = offline_backend()
    reading = backend.updates.updates(timeout=0.2)
    assert not reading.available and reading.value is None


# -- recovery ----------------------------------------------------------------------------------------
def test_firmware_setup_is_offered_only_when_logind_can_do_it(system):
    """The logind mock answers CanRebootToFirmwareSetup with an error, so the row must be absent
    rather than a switch that fails after the click."""
    assert not system.backend.power.firmware_setup().available


# -- firewall ------------------------------------------------------------------------------------------
def test_ufw_state_is_read_from_the_file_ufw_itself_writes(tmp_path):
    conf = tmp_path / "ufw.conf"
    conf.write_text("# comment\nENABLED=yes\nLOGLEVEL=low\n", encoding="utf-8")
    facet = FirewallFacet(offline_backend().system_bus, str(conf), which=lambda _name: "/usr/bin")
    status = facet.status()
    assert status.available and status.get("enabled") is True
    assert status.get("backend") == "ufw" and status.get("writable") is True


def test_no_firewall_installed_is_not_reported_as_off(tmp_path):
    facet = FirewallFacet(offline_backend().system_bus, str(tmp_path / "missing.conf"))
    status = facet.status()
    assert not status.available and status.value is None


def test_ufw_is_changed_through_pkexec_and_the_failure_is_carried(tmp_path):
    conf = tmp_path / "ufw.conf"
    conf.write_text("ENABLED=no\n", encoding="utf-8")
    calls = []

    def runner(args, **_kwargs):
        calls.append(args)
        return SimpleNamespace(returncode=1, stdout="", stderr="Request dismissed")

    facet = FirewallFacet(offline_backend().system_bus, str(conf), runner=runner,
                          which=lambda _name: "/usr/bin")
    result = facet.set_enabled(True)
    assert calls == [["pkexec", "ufw", "enable"]]
    assert not result.ok and result.error == "Request dismissed"


# -- default applications -------------------------------------------------------------------------------
def test_the_default_browser_is_written_into_mimeapps_and_read_back(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_DIRS", str(tmp_path / "empty"))
    facet = DefaultAppsFacet(home=tmp_path)
    assert not facet.role("browser").available, "nothing is set yet, and that is said plainly"
    assert facet.set_role("browser", "firefox.desktop").ok
    role = facet.role("browser")
    assert role.available and role.get("desktop_id") == "firefox.desktop"
    text = (tmp_path / ".config" / "mimeapps.list").read_text(encoding="utf-8")
    assert "x-scheme-handler/https=firefox.desktop" in text
    assert "text/html=firefox.desktop" in text


def test_writing_one_role_keeps_the_other_lines(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_DIRS", str(tmp_path / "empty"))
    facet = DefaultAppsFacet(home=tmp_path)
    facet.set_role("browser", "firefox.desktop")
    facet.set_role("music", "vlc.desktop")
    assert facet.role("browser").get("desktop_id") == "firefox.desktop"
    assert facet.role("music").get("desktop_id") == "vlc.desktop"
