# SPDX-License-Identifier: GPL-3.0-or-later
"""Incoming service calls survive synchronous outgoing RPCs on a real private bus."""
import pytest

from zaldros_backend.connection import BUS_INTERFACE, BUS_NAME, BUS_PATH, Connection, DBusError
from zaldros_backend.service import Interface, ObjectServer
from zaldros_backend.testing import SessionDaemon
from zaldros_backend.wire import METHOD_RETURN, SIGNAL, Message

pytestmark = pytest.mark.skipif(not SessionDaemon.available(), reason="dbus-daemon missing")
PATH, IFACE = "/test", "org.zaldros.Test"


@pytest.fixture
def peers():
    with SessionDaemon() as daemon:
        connections = [Connection.connect(daemon.address) for _ in range(3)]
        try:
            yield connections
        finally:
            for connection in connections:
                connection.close()


def enqueue(client, destination, labels=("first", "second")):
    serials = [client.send(Message(destination=destination, path=PATH, interface=IFACE,
                                   member="Echo", signature="s", body=[label]))
               for label in labels]
    # The daemon has routed these messages before answering this same client's barrier.
    client.list_names()
    return serials


def read_replies(client, serials):
    replies = {}
    for _ in range(20):
        message = client._read_message(0.05)
        if message and message.type == METHOD_RETURN:
            assert message.reply_serial not in replies
            replies[message.reply_serial] = message.body
        if len(replies) == len(serials):
            break
    assert replies == dict(zip(serials, [["first"], ["second"]]))


@pytest.mark.parametrize("outcome", ["success", "error", "timeout", "cancel"])
def test_incoming_calls_survive_outgoing_call_without_reentrant_execution(peers, outcome):
    server_connection, client, silent = peers
    server, seen = ObjectServer(server_connection), []
    interface = Interface(IFACE)
    interface.add_method("Echo", "s", "s", lambda label: seen.append(label) or label)
    server.add(PATH, interface)
    serials = enqueue(client, server_connection.unique_name)
    if outcome == "success":
        assert BUS_NAME in server_connection.list_names()
    elif outcome == "error":
        with pytest.raises(DBusError, match="UnknownMethod"):
            server_connection.call(Message(destination=BUS_NAME, path=BUS_PATH,
                interface=BUS_INTERFACE, member="Missing"))
    else:
        checks = 0
        def cancelled():
            nonlocal checks
            checks += 1
            # Before send, then before reading first/second incoming call, then stop.
            return checks >= 4
        with pytest.raises(DBusError, match="stopped waiting" if outcome == "cancel" else "did not answer"):
            server_connection.call(Message(destination=silent.unique_name, path=PATH,
                interface=IFACE, member="Silent"), timeout=0.15,
                cancelled=cancelled if outcome == "cancel" else None)
    assert seen == []  # No arbitrary service handlers inside a synchronous client RPC.
    assert server.process() == 2
    assert seen == ["first", "second"]
    assert server.process() == 0
    read_replies(client, serials)


def test_client_dispatch_preserves_methods_for_the_object_server(peers):
    connection, client, _ = peers
    server, seen = ObjectServer(connection), []
    interface = Interface(IFACE)
    interface.add_method("Echo", "s", "s", lambda label: seen.append(label) or label)
    server.add(PATH, interface)
    serials = enqueue(client, connection.unique_name)
    assert connection.dispatch(0.02) == 0
    assert seen == []
    assert server.process() == 2
    read_replies(client, serials)


def test_service_handler_rpc_retains_the_next_call_without_reentrant_execution(peers):
    connection, client, _ = peers
    server, seen = ObjectServer(connection), []
    def echo(label):
        seen.append((label, "start"))
        connection.list_names()
        seen.append((label, "end"))
        return label
    interface = Interface(IFACE)
    interface.add_method("Echo", "s", "s", echo)
    server.add(PATH, interface)
    serials = enqueue(client, connection.unique_name)
    assert server.process(0.02) == 2
    assert seen == [("first", "start"), ("first", "end"),
                    ("second", "start"), ("second", "end")]
    assert server.process() == 0
    read_replies(client, serials)


def test_object_server_delivers_signals_while_receiving_methods(peers):
    connection, client, _ = peers
    seen = []
    subscription = connection.subscribe(lambda message: seen.append(message.body[0]),
        sender=client.unique_name, path=PATH, interface=IFACE, member="Changed")
    try:
        client.send(Message(type=SIGNAL, path=PATH, interface=IFACE, member="Changed",
                            signature="s", body=["before"]))
        enqueue(client, connection.unique_name, ())
        connection.list_names()  # Park the first signal during this RPC.
        client.send(Message(type=SIGNAL, path=PATH, interface=IFACE, member="Changed",
                            signature="s", body=["after"]))
        client.list_names()
        assert ObjectServer(connection).process(0.02) == 0
        assert seen == ["before", "after"]
    finally:
        subscription.cancel()


def test_callback_rpc_does_not_erase_newly_parked_messages(peers):
    connection, client, _ = peers
    seen = []
    def changed(message):
        seen.append(message.body[0])
        if message.body[0] == "first":
            client.send(Message(type=SIGNAL, path=PATH, interface=IFACE, member="Changed",
                                signature="s", body=["second"]))
            client.list_names()
            connection.list_names()
    subscription = connection.subscribe(changed, sender=client.unique_name, path=PATH,
                                        interface=IFACE, member="Changed")
    try:
        client.send(Message(type=SIGNAL, path=PATH, interface=IFACE, member="Changed",
                            signature="s", body=["first"]))
        client.list_names()
        connection.list_names()
        for _ in range(3):
            connection.dispatch()
        assert seen == ["first", "second"]
    finally:
        subscription.cancel()


def test_no_reply_calls_execute_once_and_do_not_send_a_reply(peers):
    connection, client, _ = peers
    server, seen = ObjectServer(connection), []
    interface = Interface(IFACE)
    interface.add_method("Echo", "s", "s", lambda label: seen.append(label) or label)
    server.add(PATH, interface)
    client.send_no_reply(Message(destination=connection.unique_name, path=PATH,
                                interface=IFACE, member="Echo", signature="s", body=["once"]))
    client.list_names()
    connection.list_names()
    assert server.process() == 1
    assert server.process() == 0 and seen == ["once"]
    assert client._read_message(0.05) is None


def test_signal_callback_failure_retains_unhandled_calls_in_order(peers):
    connection, client, _ = peers
    server, seen = ObjectServer(connection), []
    interface = Interface(IFACE)
    interface.add_method("Echo", "s", "s", lambda label: seen.append(label) or label)
    server.add(PATH, interface)
    def broken(_message):
        raise ValueError("consumer failed")
    subscription = connection.subscribe(broken, sender=client.unique_name, path=PATH,
                                        interface=IFACE, member="Changed")
    try:
        first = enqueue(client, connection.unique_name, ("first",))
        client.send(Message(type=SIGNAL, path=PATH, interface=IFACE, member="Changed"))
        second = enqueue(client, connection.unique_name, ("second",))
        connection.list_names()
        with pytest.raises(ValueError, match="consumer failed"):
            connection.dispatch()
        assert server.process() == 2
        assert seen == ["first", "second"]
        read_replies(client, first + second)
    finally:
        subscription.cancel()


def test_service_connection_closed_during_handler_ends_processing_cleanly(peers):
    connection, client, _ = peers
    server = ObjectServer(connection)
    interface = Interface(IFACE)
    interface.add_method("Close", "", "", connection.close)
    server.add(PATH, interface)
    client.send_no_reply(Message(destination=connection.unique_name, path=PATH,
                                interface=IFACE, member="Close"))
    client.list_names()
    assert server.process(0.02) == 1
    assert server.process() == 0
    with pytest.raises(DBusError, match="reading from the bus failed"):
        connection._read_message(0)
