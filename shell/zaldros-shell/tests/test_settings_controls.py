"""The loop the whole task is about: UI change → backend → system state → UI reflects the state.

Each test here goes through `settingscontrols.Registry`, which is what a click in Settings calls.
The system underneath is a real bus with mock services, so "the UI reflects the state" means the
value was read back out of the service after the write — not out of the object we just wrote to.
"""

from __future__ import annotations

import threading
from types import SimpleNamespace

import pytest

from zaldros_backend.notifications import Notification, NotificationServer, policy_from
from zaldros_backend.testing import MockSystem, SessionDaemon, backend_on, offline_backend
from zaldros_shell import prefs, settingscontrols, settingspages

pytestmark = pytest.mark.skipif(not SessionDaemon.available(),
                                reason="dbus-daemon is not installed")


@pytest.fixture
def machine(tmp_path, monkeypatch):
    # accountsservice knows "zaldros"; the session facet reads $USER, so the mock machine and the
    # session must agree on who is logged in — as they do on a real one.
    monkeypatch.setenv("USER", "zaldros")
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
    registry = settingscontrols.Registry(backend=backend, home=tmp_path)
    try:
        yield SimpleNamespace(registry=registry, backend=backend, mock=mock, home=tmp_path)
    finally:
        stop.set()
        thread.join(timeout=2)
        backend.close()
        mock.close()
        daemon.stop()


def _round_trip(registry, control_id, value):
    """Write through the registry and return the state it read back afterwards."""
    return registry.set(control_id, value)


# -- the loop, one domain at a time ------------------------------------------------------------
def test_a_switch_reports_what_the_service_says_afterwards_not_what_was_clicked(machine):
    before = machine.registry.state("bluetooth.power")
    assert before.kind == "switch" and before.value is True
    after = machine.registry.toggle("bluetooth.power")
    assert after.value is False
    assert machine.backend.bluetooth.adapter().get("powered") is False
    assert machine.registry.state("bluetooth.power").value is False


def test_wifi_switch_reaches_networkmanager(machine):
    assert machine.registry.state("network.wifi").value is True
    assert machine.registry.toggle("network.wifi").value is False
    assert machine.backend.network.wifi_enabled().get("enabled") is False


def test_airplane_mode_turns_both_radios_off_and_says_so(machine):
    state = machine.registry.set("network.airplane", True)
    assert state.value is True
    assert machine.backend.network.wifi_enabled().get("enabled") is False
    assert machine.backend.bluetooth.adapter().get("powered") is False


def test_timezone_is_a_choice_whose_options_come_from_the_service(machine):
    state = machine.registry.state("time.timezone")
    assert state.kind == "choice" and state.value == "Europe/Moscow"
    assert {option["id"] for option in state.choices} >= {"UTC", "Asia/Jerusalem"}
    after = _round_trip(machine.registry, "time.timezone", "Asia/Jerusalem")
    assert after.value == "Asia/Jerusalem"
    assert machine.backend.localetime.clock().get("timezone") == "Asia/Jerusalem"


def test_ntp_switch_round_trips(machine):
    assert machine.registry.toggle("time.ntp").value is False
    assert machine.backend.localetime.clock().get("ntp") is False


def test_touchpad_switch_round_trips_through_kwin(machine):
    assert machine.registry.state("touchpad.tap_to_click").value is False
    assert machine.registry.toggle("touchpad.tap_to_click").value is True
    assert machine.backend.input.value_for_kind("touchpad", "tap_to_click").get("setting") is True


def test_pointer_speed_is_a_discrete_choice_that_writes_a_real_double(machine):
    state = machine.registry.state("mouse.acceleration")
    assert state.kind == "choice" and [option["id"] for option in state.choices] == \
        ["-1", "-0.5", "0", "0.5", "1"]
    after = _round_trip(machine.registry, "mouse.acceleration", "0.5")
    assert after.value == "0.5"
    assert machine.backend.input.value_for_kind("pointer", "acceleration").get("setting") == 0.5


def test_automatic_login_round_trips_through_accountsservice(machine):
    state = machine.registry.state("accounts.automatic_login")
    assert state.value is False and state.writable is True
    assert machine.registry.toggle("accounts.automatic_login").value is True
    assert machine.backend.accounts.user("zaldros").get("automatic_login") is True


def test_privacy_switch_writes_every_application_in_the_portal_store(machine):
    state = machine.registry.state("privacy.camera")
    assert state.value is False, "one denied application means the page switch reads off"
    after = machine.registry.toggle("privacy.camera")
    assert after.value is True
    assert machine.backend.permissions.device("camera").get("denied") == []


def test_updates_are_counted_by_the_row_that_shows_them(machine):
    state = machine.registry.state("updates.available")
    assert state.available and state.value == 2 and state.writable is False


def test_an_action_row_runs_and_stays_an_action(machine):
    state = machine.registry.invoke("updates.check")
    assert state.kind == "action" and state.available


# -- honesty ---------------------------------------------------------------------------------------
def test_on_a_machine_with_no_services_every_control_is_unavailable_and_none_invents_a_value():
    registry = settingscontrols.Registry(backend=offline_backend())
    invented = []
    for control_id in registry.ids():
        if control_id.startswith(("pref:", "apps.")):
            continue                       # the shell's own store and mimeapps.list are local files
        state = registry.state(control_id)
        if not state.available and state.value is not None:
            invented.append(control_id)
        if not state.available and not state.reason:
            invented.append(f"{control_id}: unavailable without a reason")
    assert not invented, invented


def test_a_write_that_the_system_refuses_comes_back_with_the_reason_and_the_old_state():
    registry = settingscontrols.Registry(backend=offline_backend())
    state = registry.set("network.wifi", True)
    assert state.value is None and state.reason


def test_every_control_row_in_the_settings_tree_exists_in_the_registry(machine):
    tree = settingspages.to_variant(settingspages.build(controls=machine.registry))
    unknown = sorted({entry["control"] for page in tree.values() for entry in page["entries"]
                      if entry.get("control") and entry["control"] not in machine.registry})
    assert not unknown, f"Settings rows point at controls that do not exist: {unknown}"


def test_every_row_that_draws_a_switch_is_a_switch_control(machine):
    tree = settingspages.to_variant(settingspages.build(controls=machine.registry))
    wrong = [(entry["title"], entry["kind"]) for page in tree.values()
             for entry in page["entries"]
             if entry["hasToggle"] and entry.get("kind") not in ("switch", "")]
    assert not wrong, wrong


def test_the_tree_still_builds_without_a_machine_under_it():
    """A pure tree test (no registry) must still produce every page, marked unwritable."""
    tree = settingspages.to_variant(settingspages.build())
    rows = [entry for page in tree.values() for entry in page["entries"] if entry.get("control")]
    assert rows and all(row["writable"] is False for row in rows)


# -- the shell's own switches ----------------------------------------------------------------------
def test_a_preference_switch_is_written_to_disk_and_read_back(machine):
    assert machine.registry.state("pref:taskbar.search").value is True
    assert machine.registry.toggle("pref:taskbar.search").value is False
    assert prefs.load(machine.home)["taskbar.search"] is False
    assert settingscontrols.Registry(backend=machine.backend,
                                     home=machine.home).state("pref:taskbar.search").value is False


def test_do_not_disturb_really_stops_banners_and_lets_critical_through():
    """The notification switches are not decoration: the server consults them for every message."""
    switches = {"notifications.banners": True, "notifications.dnd": True,
                "notifications.sound": True}
    seen: list[Notification] = []
    server = NotificationServer(seen.append, policy=policy_from(lambda: switches))
    server._notify(["app", 0, "", "Заголовок", "текст", [], {}, -1])          # noqa: SLF001
    assert seen[-1].banner is False and seen[-1].silent is True

    server._notify(["app", 0, "", "Батарея", "5 %", [], {"urgency": 2}, -1])  # noqa: SLF001
    assert seen[-1].banner is True, "a critical notification is never swallowed by DND"

    switches["notifications.dnd"] = False
    server._notify(["app", 0, "", "Обычное", "", [], {}, -1])                 # noqa: SLF001
    assert seen[-1].banner is True and seen[-1].silent is False


def test_the_clipboard_switch_stops_the_history_from_recording(tmp_path):
    """«Журнал буфера обмена» off means nothing is recorded, not that it is hidden."""
    from zaldros_shell import model

    prefs.save(dict(prefs.DEFAULTS, **{"clipboard.history": False}), tmp_path)

    class FakeClipboard:
        def text(self):
            return "секрет"

        def image(self):
            return None

        class _Signal:
            def connect(self, _handler):
                pass

        dataChanged = _Signal()

    clipboard = model.ClipboardModel(home=tmp_path, cache=tmp_path / "cache",
                                     clipboard=FakeClipboard())
    assert clipboard.capture() is False
    assert clipboard.rowCount() == 0
