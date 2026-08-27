"""A D-Bus connection: socket, SASL handshake, calls, and signal delivery.

No polling. A connection exposes `fileno()`, so the shell watches the socket with a
`QSocketNotifier` and only wakes when the bus actually has something to say. `dispatch()` drains
whatever arrived and hands signals to their subscribers.

Reference: D-Bus Specification §"Authentication Protocol" and §"Server Addresses"
(https://dbus.freedesktop.org/doc/dbus-specification.html), fetched 2026-08-27.
"""

from __future__ import annotations

import binascii
import errno
import os
import socket
import time
from dataclasses import dataclass
from typing import Any, Callable

from .wire import (ERROR, METHOD_CALL, METHOD_RETURN, NO_REPLY_EXPECTED, SIGNAL, Message,
                   WireError, message_length)

BUS_NAME = "org.freedesktop.DBus"
BUS_PATH = "/org/freedesktop/DBus"
BUS_INTERFACE = "org.freedesktop.DBus"
PROPERTIES = "org.freedesktop.DBus.Properties"
INTROSPECTABLE = "org.freedesktop.DBus.Introspectable"
OBJECT_MANAGER = "org.freedesktop.DBus.ObjectManager"

SYSTEM_BUS_FALLBACK = "unix:path=/var/run/dbus/system_bus_socket"
DEFAULT_TIMEOUT = 5.0


class DBusError(RuntimeError):
    """A bus that is not there, or a call that came back as an error. Always carries the reason."""


@dataclass(frozen=True)
class Subscription:
    """A live signal subscription. `cancel()` removes the handler and the match rule."""

    rule: str
    handler: Callable[[Message], None]
    _connection: "Connection"

    def cancel(self) -> None:
        self._connection.unsubscribe(self)


def system_bus_address() -> str:
    return os.environ.get("DBUS_SYSTEM_BUS_ADDRESS") or SYSTEM_BUS_FALLBACK


def session_bus_address() -> str:
    address = os.environ.get("DBUS_SESSION_BUS_ADDRESS")
    if address:
        return address
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if runtime:
        return f"unix:path={runtime}/bus"
    raise DBusError("no session bus address: DBUS_SESSION_BUS_ADDRESS and XDG_RUNTIME_DIR are unset")


def _parse_address(address: str) -> list[tuple[str, dict[str, str]]]:
    """One address string can hold several alternatives separated by ';'."""
    out = []
    for entry in address.split(";"):
        entry = entry.strip()
        if not entry:
            continue
        transport, _, rest = entry.partition(":")
        options = {}
        for pair in rest.split(","):
            if "=" in pair:
                key, _, value = pair.partition("=")
                options[key] = _unescape(value)
        out.append((transport, options))
    return out


def _unescape(text: str) -> str:
    out, index = [], 0
    while index < len(text):
        if text[index] == "%" and index + 2 < len(text) + 1:
            try:
                out.append(chr(int(text[index + 1:index + 3], 16)))
                index += 3
                continue
            except ValueError:
                pass
        out.append(text[index])
        index += 1
    return "".join(out)


class Connection:
    """One connection to one bus.

    Thread model: single-threaded, like the shell. Calls block on the socket with a timeout and
    park any signal that arrives in the meantime, so a signal is never lost just because it landed
    between a request and its reply.
    """

    def __init__(self, sock: socket.socket) -> None:
        self._socket = sock
        self._buffer = b""
        self._serial = 0
        self._unique_name = ""
        self._handlers: list[tuple[str, dict[str, str], Callable[[Message], None]]] = []
        self._parked: list[Message] = []
        self._closed = False

    # -- lifecycle ---------------------------------------------------------------------------
    @classmethod
    def connect(cls, address: str, timeout: float = DEFAULT_TIMEOUT) -> "Connection":
        last_error = "no usable address"
        for transport, options in _parse_address(address):
            if transport != "unix":
                last_error = f"transport {transport!r} is not supported"
                continue
            path = options.get("path")
            abstract = options.get("abstract")
            target = path if path else ("\0" + abstract if abstract else None)
            if target is None:
                last_error = "unix address without path= or abstract="
                continue
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            try:
                sock.connect(target)
            except OSError as exc:
                sock.close()
                last_error = f"{target!r}: {exc.strerror or exc}"
                continue
            connection = cls(sock)
            connection._authenticate()
            connection.hello()
            return connection
        raise DBusError(f"cannot reach the bus at {address!r}: {last_error}")

    @classmethod
    def system(cls, timeout: float = DEFAULT_TIMEOUT) -> "Connection":
        return cls.connect(system_bus_address(), timeout)

    @classmethod
    def session(cls, timeout: float = DEFAULT_TIMEOUT) -> "Connection":
        return cls.connect(session_bus_address(), timeout)

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            try:
                self._socket.close()
            except OSError:
                pass

    @property
    def closed(self) -> bool:
        return self._closed

    def fileno(self) -> int:
        return self._socket.fileno()

    @property
    def unique_name(self) -> str:
        return self._unique_name

    # -- handshake ---------------------------------------------------------------------------
    def _authenticate(self) -> None:
        """SASL EXTERNAL, the mechanism every Linux bus accepts for a local uid."""
        self._socket.sendall(b"\0")
        uid = binascii.hexlify(str(os.getuid()).encode("ascii")).decode("ascii")
        reply = self._command(f"AUTH EXTERNAL {uid}")
        if not reply.startswith("OK"):
            reply = self._command("AUTH ANONYMOUS 5a616c64726f73")   # "Zaldros"
            if not reply.startswith("OK"):
                raise DBusError(f"the bus refused authentication: {reply!r}")
        self._socket.sendall(b"BEGIN\r\n")

    def _command(self, text: str) -> str:
        self._socket.sendall(text.encode("ascii") + b"\r\n")
        line = b""
        while not line.endswith(b"\r\n"):
            chunk = self._socket.recv(1)
            if not chunk:
                raise DBusError("the bus closed the connection during authentication")
            line += chunk
        return line.decode("ascii", "replace").strip()

    def hello(self) -> str:
        reply = self.call(Message(type=METHOD_CALL, destination=BUS_NAME, path=BUS_PATH,
                                  interface=BUS_INTERFACE, member="Hello"))
        self._unique_name = reply.body[0] if reply.body else ""
        return self._unique_name

    # -- sending -----------------------------------------------------------------------------
    def _next_serial(self) -> int:
        self._serial += 1
        return self._serial

    def send(self, message: Message) -> int:
        if self._closed:
            raise DBusError("the connection is closed")
        message.serial = self._next_serial()
        try:
            self._socket.sendall(message.to_bytes())
        except OSError as exc:
            self.close()
            raise DBusError(f"sending {message.member} failed: {exc.strerror or exc}") from exc
        return message.serial

    def call(self, message: Message, timeout: float = DEFAULT_TIMEOUT) -> Message:
        """Send and wait for the matching reply. Raises DBusError on an error reply or a timeout."""
        message.type = METHOD_CALL
        serial = self.send(message)
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise DBusError(f"{message.interface}.{message.member} did not answer in {timeout}s")
            reply = self._read_message(remaining)
            if reply is None:
                continue
            if reply.reply_serial == serial:
                if reply.is_error:
                    raise DBusError(reply.error_text())
                if reply.type != METHOD_RETURN:
                    raise DBusError(f"unexpected reply type {reply.type}")
                return reply
            self._park(reply)

    def send_no_reply(self, message: Message) -> None:
        message.type = METHOD_CALL
        message.flags |= NO_REPLY_EXPECTED
        self.send(message)

    # -- receiving ---------------------------------------------------------------------------
    def _read_message(self, timeout: float) -> Message | None:
        message = self._take_buffered()
        if message is not None:
            return message
        self._socket.settimeout(max(0.0, timeout))
        try:
            chunk = self._socket.recv(65536)
        except socket.timeout:
            return None
        except OSError as exc:
            if exc.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
                return None
            self.close()
            raise DBusError(f"reading from the bus failed: {exc.strerror or exc}") from exc
        if not chunk:
            self.close()
            raise DBusError("the bus closed the connection")
        self._buffer += chunk
        return self._take_buffered()

    def _take_buffered(self) -> Message | None:
        length = message_length(self._buffer)
        if length is None or len(self._buffer) < length:
            return None
        raw, self._buffer = self._buffer[:length], self._buffer[length:]
        try:
            message, _ = Message.from_bytes(raw)
        except WireError as exc:
            raise DBusError(f"the bus sent something we cannot parse: {exc}") from exc
        return message

    def _park(self, message: Message) -> None:
        if message.type == SIGNAL:
            self._parked.append(message)
        # Stray method returns and errors for calls nobody is waiting on are dropped: the caller
        # that would have cared has already timed out and reported it.

    def dispatch(self, timeout: float = 0.0) -> int:
        """Deliver everything that has arrived. Returns how many signals were delivered.

        Called from the socket notifier, so `timeout=0`: read what is there, deliver, return.
        """
        delivered = 0
        for message in self._parked:
            delivered += self._deliver(message)
        self._parked = []
        deadline = time.monotonic() + timeout
        while True:
            message = self._read_message(max(0.0, deadline - time.monotonic()))
            if message is None:
                break
            if message.type == SIGNAL:
                delivered += self._deliver(message)
            if timeout <= 0 and not self._buffer:
                # One recv per dispatch when we are not waiting: the notifier will fire again.
                break
        return delivered

    def _deliver(self, message: Message) -> int:
        count = 0
        for _rule, criteria, handler in list(self._handlers):
            if _matches(criteria, message):
                handler(message)
                count += 1
        return count

    # -- signals -----------------------------------------------------------------------------
    def subscribe(self, handler: Callable[[Message], None], *, sender: str | None = None,
                  path: str | None = None, path_namespace: str | None = None,
                  interface: str | None = None, member: str | None = None,
                  arg0: str | None = None) -> Subscription:
        """Ask the bus for a class of signals and route them to `handler`.

        `path_namespace` is what makes NetworkManager, BlueZ and udisks2 affordable: one match
        rule covers every device object under a prefix, instead of one rule per object plus a
        re-subscription every time hardware appears.
        """
        criteria: dict[str, str] = {"type": "signal"}
        for key, value in (("sender", sender), ("path", path), ("path_namespace", path_namespace),
                           ("interface", interface), ("member", member), ("arg0", arg0)):
            if value is not None:
                criteria[key] = value
        rule = ",".join(f"{key}='{value}'" for key, value in criteria.items())
        # (`rule` is built before the synthetic key below: the bus would reject an unknown key.)
        # The bus filters by sender for us, but every message that matches *any* of this
        # connection's rules is delivered on the one socket, and then our own dispatcher decides
        # who wanted it. It cannot compare senders as written: a signal's `sender` field is the
        # unique name (":1.7"), never the well-known one. Without resolving it here, a udisks2
        # InterfacesAdded also woke the BlueZ handler — measured, then fixed.
        if sender and not sender.startswith(":"):
            criteria["sender_unique"] = self._owner_of(sender)
        self.call(Message(destination=BUS_NAME, path=BUS_PATH, interface=BUS_INTERFACE,
                          member="AddMatch", signature="s", body=[rule]))
        self._handlers.append((rule, criteria, handler))
        return Subscription(rule, handler, self)

    def unsubscribe(self, subscription: Subscription) -> None:
        before = len(self._handlers)
        self._handlers = [entry for entry in self._handlers
                          if not (entry[0] == subscription.rule
                                  and entry[2] is subscription.handler)]
        if len(self._handlers) == before:
            return
        if any(entry[0] == subscription.rule for entry in self._handlers):
            return  # another subscriber still wants this rule
        if self._closed:
            return
        try:
            self.call(Message(destination=BUS_NAME, path=BUS_PATH, interface=BUS_INTERFACE,
                              member="RemoveMatch", signature="s", body=[subscription.rule]))
        except DBusError:
            pass  # the bus is going away; the rule dies with the connection

    @property
    def subscription_count(self) -> int:
        return len(self._handlers)

    # -- convenience -------------------------------------------------------------------------
    def _owner_of(self, name: str) -> str:
        """The unique name behind a well-known one, or "" when nobody owns it (yet)."""
        try:
            reply = self.call(Message(destination=BUS_NAME, path=BUS_PATH,
                                      interface=BUS_INTERFACE, member="GetNameOwner",
                                      signature="s", body=[name]))
        except DBusError:
            return ""
        return str(reply.body[0]) if reply.body else ""

    def name_has_owner(self, name: str) -> bool:
        reply = self.call(Message(destination=BUS_NAME, path=BUS_PATH, interface=BUS_INTERFACE,
                                  member="NameHasOwner", signature="s", body=[name]))
        return bool(reply.body and reply.body[0])

    def list_names(self) -> list[str]:
        reply = self.call(Message(destination=BUS_NAME, path=BUS_PATH, interface=BUS_INTERFACE,
                                  member="ListNames"))
        return list(reply.body[0]) if reply.body else []


def _matches(criteria: dict[str, str], message: Message) -> bool:
    unique = criteria.get("sender_unique")
    if unique and message.sender and message.sender != unique:
        return False
    if criteria.get("interface") and message.interface != criteria["interface"]:
        return False
    if criteria.get("member") and message.member != criteria["member"]:
        return False
    if criteria.get("path") and message.path != criteria["path"]:
        return False
    namespace = criteria.get("path_namespace")
    if namespace and not (message.path == namespace
                          or (message.path or "").startswith(namespace.rstrip("/") + "/")):
        return False
    if criteria.get("arg0"):
        first = message.body[0] if message.body else None
        if not isinstance(first, str) or first != criteria["arg0"]:
            return False
    return True
