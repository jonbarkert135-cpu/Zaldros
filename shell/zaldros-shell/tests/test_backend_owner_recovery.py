# SPDX-License-Identifier: GPL-3.0-or-later
"""Fault injection on a real private bus; test services are not system daemons."""

import time

import pytest

from zaldros_backend import Bus, Connection, DBusError
from zaldros_backend.connection import BUS_INTERFACE, BUS_PATH
from zaldros_backend.service import ObjectServer
from zaldros_backend.testing import SessionDaemon
from zaldros_backend.wire import Message, SIGNAL

NAME = "org.zaldros.TestRecovery"
OTHER = "org.zaldros.TestOther"
PATH = "/org/zaldros/TestRecovery"
IFACE = "org.zaldros.TestRecovery"

pytestmark = pytest.mark.skipif(not SessionDaemon.available(), reason="dbus-daemon missing")


@pytest.fixture
def peers():
    with SessionDaemon() as daemon:
        connections = []

        def connect():
            connection = Connection.connect(daemon.address)
            connections.append(connection)
            return connection

        yield connect
        for connection in connections:
            connection.close()


def own(connection, name=NAME):
    server = ObjectServer(connection)
    assert server.request_name(name)
    return server


def emit(connection, value):
    connection.send(Message(type=SIGNAL, path=PATH, interface=IFACE, member="Changed",
                            signature="s", body=[value]))
    connection.list_names()  # daemon has routed this signal before another peer sends


def drain(connection):
    # A daemon round trip is a barrier: earlier routed signals have reached this socket.
    connection.list_names()
    return connection.dispatch(0)


def subscribe(connection, seen, sender=NAME):
    return connection.subscribe(lambda message: seen.append(message.body[0]), sender=sender,
                                path=PATH, interface=IFACE, member="Changed")


def test_repeated_service_restart_recovers_existing_subscription_without_duplicates(peers):
    client, service = peers(), peers()
    own(service)
    seen = []
    subscription = subscribe(client, seen)
    emit(service, "initial")
    drain(client)
    for attempt in range(3):
        service.close()
        replacement = peers()
        own(replacement)
        emit(replacement, f"restart-{attempt}")
        drain(client)
        service = replacement
    assert seen == ["initial", "restart-0", "restart-1", "restart-2"]
    assert client.subscription_count == 1
    subscription.cancel()
    emit(service, "cancelled")
    drain(client)
    assert len(seen) == 4
    assert client.subscription_count == 0


def test_missing_service_never_accepts_other_sender_then_recovers_on_start(peers):
    client, other = peers(), peers()
    own(other, OTHER)
    seen, other_seen = [], []
    subscribe(client, seen)
    subscribe(client, other_seen, OTHER)  # same interface/path: both arrive on one socket
    emit(other, "other")
    drain(client)
    assert seen == []
    assert other_seen == ["other"]
    service = peers()
    own(service)
    emit(service, "started")
    drain(client)
    assert seen == ["started"]
    assert other_seen == ["other"]


def test_unique_sender_subscription_is_not_a_wildcard(peers):
    client, service, other = peers(), peers(), peers()
    seen, broad = [], []
    subscribe(client, seen, service.unique_name)
    client.subscribe(lambda message: broad.append(message.body[0]), path=PATH,
                     interface=IFACE, member="Changed")
    emit(other, "unrelated")
    emit(service, "expected")
    drain(client)
    assert seen == ["expected"]
    assert broad == ["unrelated", "expected"]


def test_forged_name_owner_signal_does_not_rebind_subscription(peers):
    client, service, other = peers(), peers(), peers()
    own(service)
    seen = []
    subscribe(client, seen)
    client.subscribe(lambda message: None, interface=BUS_INTERFACE, member="NameOwnerChanged")
    other.send(Message(type=SIGNAL, path=BUS_PATH, interface=BUS_INTERFACE,
                       member="NameOwnerChanged", signature="sss",
                       body=[NAME, service.unique_name, other.unique_name]))
    other.list_names()
    emit(service, "still-valid")
    drain(client)
    assert seen == ["still-valid"]


def test_owner_changes_invalidate_service_presence_cache_after_dispatch(peers):
    client, service = peers(), peers()
    own(service)
    bus = Bus(connection=client)
    subscribe(client, [])
    assert bus.has_service(NAME, max_age=3600)
    service.close()
    deadline = time.monotonic() + 1
    while client.name_has_owner(NAME) and time.monotonic() < deadline:
        time.sleep(0.001)
    assert not client.name_has_owner(NAME)
    drain(client)
    assert not bus.has_service(NAME, max_age=3600)
    replacement = peers()
    own(replacement)
    drain(client)
    assert bus.has_service(NAME, max_age=3600)


def test_shared_rule_is_removed_after_last_cancel_and_can_be_resubscribed(peers):
    client, service = peers(), peers()
    own(service)
    first_seen, second_seen = [], []
    first = subscribe(client, first_seen)
    second = subscribe(client, second_seen)
    first.cancel()
    first.cancel()
    emit(service, "one-listener")
    drain(client)
    assert first_seen == []
    assert second_seen == ["one-listener"]
    second.cancel()
    emit(service, "no-listeners")
    # dispatch returns how many handlers were called, so inspect raw parked messages too:
    client.list_names()
    assert not [message for message in client._parked if message.interface == IFACE]
    drain(client)
    own(service, OTHER)
    client.list_names()
    assert not [message for message in client._parked if message.member == "NameOwnerChanged"]
    third = subscribe(client, first_seen)
    service.close()
    replacement = peers()
    own(replacement)
    emit(replacement, "resubscribed")
    drain(client)
    assert first_seen == ["resubscribed"]
    third.cancel()


def test_failed_subscription_removes_its_owner_watch(peers):
    client, service = peers(), peers()
    with pytest.raises(DBusError):
        client.subscribe(lambda message: None, sender=NAME, path="invalid-object-path")
    assert client.subscription_count == 0
    drain(client)
    own(service)
    client.list_names()
    assert not [message for message in client._parked if message.member == "NameOwnerChanged"]


def test_bluez_restart_reaches_existing_facade_and_qt_bridge(peers, qt_app):
    from PySide6.QtTest import QTest

    from zaldros_backend import ZaldrosBackend
    from zaldros_backend.qtbridge import BackendBridge
    from zaldros_backend.service import Interface

    client, service = peers(), peers()
    server = own(service, "org.bluez")
    server.add("/org/bluez/hci0", Interface("org.bluez.Adapter1"))
    session = Bus("session")
    session._next_attempt = float("inf")  # never touch the host session bus
    backend = ZaldrosBackend(system_bus=Bus(connection=client), session_bus=session)
    bridge = BackendBridge(backend)
    seen = []
    bridge.changed.connect(seen.append)

    def wait_for_count(count):
        deadline = time.monotonic() + 2
        while len(seen) < count and time.monotonic() < deadline:
            QTest.qWait(10)
        assert seen == ["bluetooth"] * count

    try:
        watched = bridge.watched_sockets
        subscriptions = client.subscription_count
        server.emit_interfaces_added("/org/bluez/hci0")
        wait_for_count(1)
        service.close()
        replacement = peers()
        server = own(replacement, "org.bluez")
        server.add("/org/bluez/hci0", Interface("org.bluez.Adapter1"))
        server.emit_interfaces_added("/org/bluez/hci0")
        wait_for_count(2)
        QTest.qWait(200)  # one coalesced domain notification, no delayed duplicate
        assert seen == ["bluetooth", "bluetooth"]
        assert client.subscription_count == subscriptions
        assert bridge.watched_sockets == watched == 1
    finally:
        bridge.detach()
        bridge._timer.stop()
        bridge.deleteLater()
        backend.close()
