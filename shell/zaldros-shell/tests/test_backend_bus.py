"""The bus layer, against a real `dbus-daemon`.

Not a fake. Each test starts a private session bus, stands the mock services on it — each on its
own connection, the way separate daemons are arranged on a real machine — and drives the backend
over the wire. If the marshalling, the match rules or the signal routing are wrong, these fail.

They skip, loudly, when `dbus-daemon` is not installed rather than passing on a stub.
"""

from __future__ import annotations

import threading
import time

import pytest

from zaldros_backend import Bus, Connection, DBusError, ZaldrosBackend
from zaldros_backend.testing import MockSystem, SessionDaemon, backend_on
from zaldros_backend.wire import Message, Variant

pytestmark = pytest.mark.skipif(not SessionDaemon.available(),
                                reason="dbus-daemon is not installed")


class Bench:
    """A private bus with the mocks answering in a background thread."""

    def __init__(self) -> None:
        self.daemon = SessionDaemon()
        self.daemon.start()
        self.mock = MockSystem(self.daemon.address)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def serve(self) -> None:
        def loop() -> None:
            while not self._stop.is_set():
                self.mock.process(0.01)
        self._thread = threading.Thread(target=loop, daemon=True)
        self._thread.start()

    def backend(self) -> ZaldrosBackend:
        return backend_on(self.daemon.address)

    def close(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
        self.mock.close()
        self.daemon.stop()


@pytest.fixture
def bench():
    bench = Bench()
    try:
        yield bench
    finally:
        bench.close()


# -- the connection itself ---------------------------------------------------------------------
def test_a_connection_authenticates_and_gets_a_unique_name(bench):
    connection = Connection.connect(bench.daemon.address)
    assert connection.unique_name.startswith(":")
    assert "org.freedesktop.DBus" in connection.list_names()
    connection.close()


def test_an_unknown_method_comes_back_as_an_error_not_a_hang(bench):
    connection = Connection.connect(bench.daemon.address)
    with pytest.raises(DBusError) as raised:
        connection.call(Message(destination="org.freedesktop.DBus", path="/org/freedesktop/DBus",
                                interface="org.freedesktop.DBus", member="NoSuchMethod"))
    assert "UnknownMethod" in str(raised.value)
    connection.close()


def test_an_unreachable_bus_is_a_reason_not_an_exception():
    """The whole point of `Result`: a missing service must not be able to crash a panel."""
    bus = Bus("system", connection=None)
    bus._next_attempt = time.monotonic() + 1000     # noqa: SLF001 - pin "already tried, failed"
    bus._failure = "no bus here"                    # noqa: SLF001
    result = bus.get("org.freedesktop.UPower", "/x", "org.freedesktop.UPower", "OnBattery")
    assert not result.ok and result.error and result.value is None
    assert not bus.available


def test_property_dictionaries_decode_over_the_real_wire(bench):
    """The reason this layer exists: `GetAll` must come back as a usable dictionary."""
    bench.mock.add_upower()
    bench.serve()
    bus = Bus("system", connection=Connection.connect(bench.daemon.address))
    result = bus.get_all("org.freedesktop.UPower",
                         "/org/freedesktop/UPower/devices/DisplayDevice",
                         "org.freedesktop.UPower.Device")
    assert result.ok
    assert result.value["Percentage"] == 87.0
    assert result.value["IconName"] == "battery-good-symbolic"
    assert isinstance(result.value["IsPresent"], bool)


def test_managed_objects_returns_the_whole_tree_in_one_call(bench):
    bench.mock.add_bluez()
    bench.serve()
    bus = Bus("system", connection=Connection.connect(bench.daemon.address))
    result = bus.managed_objects("org.bluez", "/")
    assert result.ok
    assert "/org/bluez/hci0" in result.value
    assert "org.bluez.Adapter1" in result.value["/org/bluez/hci0"]


def test_setting_a_property_reaches_the_service(bench):
    bench.mock.add_bluez(powered=False)
    bench.serve()
    backend = bench.backend()
    assert backend.bluetooth.adapter().get("powered") is False
    assert backend.bluetooth.set_powered(True).ok
    assert backend.bluetooth.adapter().get("powered") is True


# -- signals -----------------------------------------------------------------------------------
def test_a_property_change_wakes_only_the_domain_it_belongs_to(bench):
    """Routing, not just delivery.

    Two services on two connections send one signal each. The bus filters by sender, but every
    matching message arrives on our one socket, and a signal's sender is the *unique* name — so
    without resolving well-known names, a udisks2 signal also woke the BlueZ handler. It did,
    once. This is the test that keeps it fixed.
    """
    bench.mock.add_all()
    bench.serve()
    backend = bench.backend()
    seen: list[str] = []
    for domain in ("power", "network", "bluetooth", "storage"):
        backend.subscribe(domain, lambda domain=domain: seen.append(domain))

    bench.mock.service("org.freedesktop.UPower").set_property(
        "/org/freedesktop/UPower/devices/DisplayDevice", "org.freedesktop.UPower.Device",
        "Percentage", Variant("d", 42.0))
    bench.mock.service("org.freedesktop.UDisks2").emit_interfaces_added(
        "/org/freedesktop/UDisks2/block_devices/sdb1")

    _wait_for(backend, expected=2)
    assert sorted(backend.flush()) == ["power", "storage"]
    assert sorted(seen) == ["power", "storage"]
    assert backend.power.battery().value == 42


def test_a_burst_of_signals_becomes_one_notification(bench):
    """NetworkManager emits many PropertiesChanged while associating; the tray rebuilds once."""
    bench.mock.add_network_manager()
    bench.serve()
    backend = bench.backend()
    calls: list[int] = []
    backend.subscribe("network", lambda: calls.append(1))
    manager = bench.mock.service("org.freedesktop.NetworkManager")
    for state in (40, 50, 60, 70):
        manager.set_property("/org/freedesktop/NetworkManager",
                             "org.freedesktop.NetworkManager", "State", Variant("u", state))
    _wait_for(backend, expected=4)
    assert backend.flush() == ["network"]
    assert len(calls) == 1


def test_nothing_is_delivered_to_a_domain_nobody_subscribed_to(bench):
    bench.mock.add_all()
    bench.serve()
    backend = bench.backend()
    backend.subscribe("power", lambda: None)
    assert backend.status()["watching"] == {"power": 3}
    bench.mock.service("org.bluez").set_property(
        "/org/bluez/hci0", "org.bluez.Adapter1", "Powered", Variant("b", False))
    time.sleep(0.2)
    backend.dispatch(0.2)
    assert backend.pending == set()


def test_the_backend_reports_what_it_is_connected_to(bench):
    bench.mock.add_all()
    bench.serve()
    backend = bench.backend()
    backend.subscribe("power", lambda: None)
    status = backend.status()
    assert status["system_bus"] and status["session_bus"]
    assert status["match_rules"] == 3
    assert status["system_bus_error"] == ""


def _wait_for(backend, expected: int, timeout: float = 3.0) -> None:
    deadline = time.monotonic() + timeout
    received = 0
    while received < expected and time.monotonic() < deadline:
        received += backend.dispatch(0.05)
