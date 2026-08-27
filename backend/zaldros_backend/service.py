"""The server side: publishing objects on a bus.

Zaldros needs this twice. It has to *be* `org.freedesktop.Notifications`, because in Windows the
notification centre is part of the shell and not a separate daemon. And it is how the backend can
later offer `org.zaldros.Backend1` to Zaldros's own applications, so Sheets and Settings ask the
shell instead of each opening their own connection to five system services.

It is also what the test suite stands mock UPower, NetworkManager, BlueZ and udisks2 on: mocks
built here answer over a real `dbus-daemon`, on the real wire format, so a facet test exercises
the same code path a real service would.

`org.freedesktop.DBus.Properties`, `.Introspectable` and `.ObjectManager` are implemented for
every object, because a client that cannot introspect is a client that cannot debug.
"""

from __future__ import annotations

from typing import Any, Callable

from .connection import Connection, DBusError
from .wire import (ERROR, METHOD_CALL, METHOD_RETURN, NO_REPLY_EXPECTED, SIGNAL, Message,
                   Variant)

PROPERTIES = "org.freedesktop.DBus.Properties"
INTROSPECTABLE = "org.freedesktop.DBus.Introspectable"
OBJECT_MANAGER = "org.freedesktop.DBus.ObjectManager"
PEER = "org.freedesktop.DBus.Peer"

# RequestName flags and replies (D-Bus Specification, "Message Bus Names").
NAME_FLAG_REPLACE_EXISTING = 0x2
NAME_FLAG_DO_NOT_QUEUE = 0x4
NAME_REPLY_PRIMARY_OWNER = 1
NAME_REPLY_ALREADY_OWNER = 3


class Method:
    """One exported method: its signatures and the Python callable behind it."""

    __slots__ = ("in_signature", "out_signature", "handler")

    def __init__(self, in_signature: str, out_signature: str,
                 handler: Callable[..., Any]) -> None:
        self.in_signature = in_signature
        self.out_signature = out_signature
        self.handler = handler


class Interface:
    """A set of properties and methods under one interface name on one object."""

    def __init__(self, name: str, properties: dict[str, Variant] | None = None) -> None:
        self.name = name
        self.properties: dict[str, Variant] = dict(properties or {})
        self.methods: dict[str, Method] = {}

    def method(self, name: str, in_signature: str = "", out_signature: str = ""):
        def register(function: Callable[..., Any]) -> Callable[..., Any]:
            self.methods[name] = Method(in_signature, out_signature, function)
            return function
        return register

    def add_method(self, name: str, in_signature: str, out_signature: str,
                   handler: Callable[..., Any]) -> None:
        self.methods[name] = Method(in_signature, out_signature, handler)

    def plain_properties(self) -> dict[str, Variant]:
        return dict(self.properties)


class ObjectServer:
    """Objects published on one connection.

    Single-threaded like everything else here: `process()` handles whatever has arrived and
    returns. The caller decides whether that is a socket notifier, a test loop or a thread.
    """

    def __init__(self, connection: Connection) -> None:
        self.connection = connection
        self.objects: dict[str, dict[str, Interface]] = {}
        self._names: list[str] = []

    # -- publishing --------------------------------------------------------------------------
    def add(self, path: str, interface: Interface) -> Interface:
        self.objects.setdefault(path, {})[interface.name] = interface
        return interface

    def remove(self, path: str, interface_name: str | None = None) -> None:
        if interface_name is None:
            self.objects.pop(path, None)
            return
        interfaces = self.objects.get(path)
        if interfaces:
            interfaces.pop(interface_name, None)
            if not interfaces:
                self.objects.pop(path, None)

    def request_name(self, name: str, replace: bool = False) -> bool:
        flags = NAME_FLAG_DO_NOT_QUEUE | (NAME_FLAG_REPLACE_EXISTING if replace else 0)
        reply = self.connection.call(Message(
            destination="org.freedesktop.DBus", path="/org/freedesktop/DBus",
            interface="org.freedesktop.DBus", member="RequestName", signature="su",
            body=[name, flags]))
        code = int(reply.body[0]) if reply.body else 0
        if code in (NAME_REPLY_PRIMARY_OWNER, NAME_REPLY_ALREADY_OWNER):
            self._names.append(name)
            return True
        return False

    @property
    def names(self) -> list[str]:
        return list(self._names)

    # -- change notification -------------------------------------------------------------------
    def set_property(self, path: str, interface_name: str, name: str, value: Variant,
                     emit: bool = True) -> None:
        """Change a property and tell the bus, which is what a real service does."""
        interface = self.objects.get(path, {}).get(interface_name)
        if interface is None:
            raise KeyError(f"{path} has no {interface_name}")
        interface.properties[name] = value
        if emit:
            self.emit_properties_changed(path, interface_name, {name: value})

    def emit_properties_changed(self, path: str, interface_name: str,
                                changed: dict[str, Variant],
                                invalidated: list[str] | None = None) -> None:
        self.connection.send(Message(
            type=SIGNAL, path=path, interface=PROPERTIES, member="PropertiesChanged",
            signature="sa{sv}as", body=[interface_name, changed, invalidated or []]))

    def emit_interfaces_added(self, path: str) -> None:
        payload = {name: interface.plain_properties()
                   for name, interface in self.objects.get(path, {}).items()}
        self.connection.send(Message(
            type=SIGNAL, path="/", interface=OBJECT_MANAGER, member="InterfacesAdded",
            signature="oa{sa{sv}}", body=[path, payload]))

    def emit_interfaces_removed(self, path: str, interfaces: list[str]) -> None:
        self.connection.send(Message(
            type=SIGNAL, path="/", interface=OBJECT_MANAGER, member="InterfacesRemoved",
            signature="oas", body=[path, interfaces]))

    def emit_signal(self, path: str, interface_name: str, member: str, signature: str = "",
                    body: list[Any] | None = None) -> None:
        self.connection.send(Message(type=SIGNAL, path=path, interface=interface_name,
                                     member=member, signature=signature, body=body or []))

    # -- serving -----------------------------------------------------------------------------
    def process(self, timeout: float = 0.0) -> int:
        """Answer whatever has arrived. Returns how many calls were handled."""
        handled = 0
        while True:
            try:
                message = self.connection._read_message(timeout)     # noqa: SLF001 - same package
            except DBusError:
                return handled
            if message is None:
                return handled
            if message.type == METHOD_CALL:
                reply = self.handle(message)
                if reply is not None and not message.flags & NO_REPLY_EXPECTED:
                    self.connection.send(reply)
                handled += 1
            timeout = 0.0

    def handle(self, message: Message) -> Message | None:
        try:
            return self._handle(message)
        except Exception as exc:            # noqa: BLE001 - an error reply, never a dead service
            return _error(message, "org.zaldros.Error.Failed", f"{type(exc).__name__}: {exc}")

    def _handle(self, message: Message) -> Message | None:
        path, interface_name, member = message.path or "", message.interface or "", message.member

        if interface_name == PEER:
            if member == "Ping":
                return _reply(message, "", [])
            if member == "GetMachineId":
                return _reply(message, "s", ["00000000000000000000000000000000"])

        if interface_name == PROPERTIES:
            return self._properties(message)

        if interface_name == OBJECT_MANAGER and member == "GetManagedObjects":
            prefix = path.rstrip("/")
            managed = {
                object_path: {name: interface.plain_properties()
                              for name, interface in interfaces.items()}
                for object_path, interfaces in self.objects.items()
                if object_path == path or object_path.startswith(prefix + "/")}
            return _reply(message, "a{oa{sa{sv}}}", [managed])

        if interface_name == INTROSPECTABLE and member == "Introspect":
            return _reply(message, "s", [self._introspect(path)])

        interface = self.objects.get(path, {}).get(interface_name)
        if interface is None:
            return _error(message, "org.freedesktop.DBus.Error.UnknownInterface",
                          f"{path} does not implement {interface_name}")
        method = interface.methods.get(member or "")
        if method is None:
            return _error(message, "org.freedesktop.DBus.Error.UnknownMethod",
                          f"{interface_name} has no member {member}")
        value = method.handler(*message.body)
        if not method.out_signature:
            return _reply(message, "", [])
        body = list(value) if isinstance(value, tuple) else [value]
        return _reply(message, method.out_signature, body)

    def _properties(self, message: Message) -> Message:
        body = list(message.body) + [None, None, None]
        interface_name = str(body[0] or "")
        interfaces = self.objects.get(message.path or "", {})
        interface = interfaces.get(interface_name)
        if message.member == "GetAll":
            if interface is None:
                return _reply(message, "a{sv}", [{}])
            return _reply(message, "a{sv}", [interface.plain_properties()])
        if interface is None:
            return _error(message, "org.freedesktop.DBus.Error.UnknownInterface",
                          f"no {interface_name} on {message.path}")
        name = str(body[1] or "")
        if message.member == "Get":
            if name not in interface.properties:
                return _error(message, "org.freedesktop.DBus.Error.UnknownProperty", name)
            return _reply(message, "v", [interface.properties[name]])
        if message.member == "Set":
            value = body[2]
            if name not in interface.properties:
                return _error(message, "org.freedesktop.DBus.Error.UnknownProperty", name)
            signature = interface.properties[name].signature
            interface.properties[name] = Variant(signature, value)
            self.emit_properties_changed(message.path or "", interface_name,
                                         {name: interface.properties[name]})
            return _reply(message, "", [])
        return _error(message, "org.freedesktop.DBus.Error.UnknownMethod", str(message.member))

    def _introspect(self, path: str) -> str:
        rows = ['<!DOCTYPE node PUBLIC "-//freedesktop//DTD D-BUS Object Introspection 1.0//EN"',
                ' "http://www.freedesktop.org/standards/dbus/1.0/introspect.dtd">', "<node>"]
        for name, interface in self.objects.get(path, {}).items():
            rows.append(f'  <interface name="{name}">')
            for property_name, value in interface.properties.items():
                rows.append(f'    <property name="{property_name}" type="{value.signature}" '
                            f'access="readwrite"/>')
            for method_name, method in interface.methods.items():
                rows.append(f'    <method name="{method_name}">')
                for index, part in enumerate(_split(method.in_signature)):
                    rows.append(f'      <arg name="arg{index}" type="{part}" direction="in"/>')
                for index, part in enumerate(_split(method.out_signature)):
                    rows.append(f'      <arg name="out{index}" type="{part}" direction="out"/>')
                rows.append("    </method>")
            rows.append("  </interface>")
        prefix = path.rstrip("/") + "/"
        children = sorted({other[len(prefix):].split("/")[0] for other in self.objects
                           if other.startswith(prefix) and other != path})
        rows.extend(f'  <node name="{child}"/>' for child in children if child)
        rows.append("</node>")
        return "\n".join(rows)


def _split(signature: str) -> list[str]:
    from .wire import split_signature
    return split_signature(signature) if signature else []


def _reply(message: Message, signature: str, body: list[Any]) -> Message:
    return Message(type=METHOD_RETURN, reply_serial=message.serial,
                   destination=message.sender, signature=signature, body=body)


def _error(message: Message, name: str, text: str) -> Message:
    return Message(type=ERROR, reply_serial=message.serial, destination=message.sender,
                   error_name=name, signature="s", body=[text])
