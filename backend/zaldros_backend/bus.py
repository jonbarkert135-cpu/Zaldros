"""The one place in Zaldros that talks D-Bus.

`Bus` is deliberately boring: nothing it does raises. Every call returns a `Result` that either
holds a value or the reason there is none, because a desktop shell must survive a service that is
not installed, not running, or answering slowly, and it must be able to *say* which of those it is.

`Bus` is also lazy. Constructing one connects to nothing; the socket is opened on first use, and
if the bus is unreachable the reason is remembered and every call answers with it immediately
instead of stalling the UI for a timeout each time.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from . import catalog
from .connection import Connection, DBusError, Subscription
from .wire import Message, Variant

RETRY_AFTER_SECONDS = 20.0     # a service that was absent is asked about again this often


@dataclass(frozen=True)
class Result:
    """The answer to one bus question: a value, or why there is not one.

    `ok=False` is a normal outcome, not an exception. `error` is written for a log; the UI uses
    the facets' own Russian wording, never this string.
    """

    ok: bool
    value: Any = None
    error: str = ""
    source: str = ""

    def __bool__(self) -> bool:
        return self.ok

    @classmethod
    def good(cls, value: Any, source: str = "") -> "Result":
        return cls(True, value, "", source)

    @classmethod
    def bad(cls, error: str, source: str = "") -> "Result":
        return cls(False, None, error, source)

    def unwrap_or(self, default: Any) -> Any:
        return self.value if self.ok else default


class Bus:
    """A lazily-connected bus with a non-raising API."""

    def __init__(self, kind: str = "system", connection: Connection | None = None,
                 timeout: float = 5.0) -> None:
        if kind not in ("system", "session"):
            raise ValueError(f"a bus is 'system' or 'session', not {kind!r}")
        self.kind = kind
        self.timeout = timeout
        self._connection = connection
        self._failure = ""
        self._next_attempt = 0.0
        self._name_cache: dict[str, tuple[float, bool]] = {}

    # -- connection --------------------------------------------------------------------------
    @property
    def connection(self) -> Connection | None:
        if self._connection is not None and not self._connection.closed:
            return self._connection
        if self._connection is not None and self._connection.closed:
            self._connection = None
            self._failure = "the bus connection dropped"
        if time.monotonic() < self._next_attempt:
            return None
        try:
            self._connection = (Connection.system(self.timeout) if self.kind == "system"
                                else Connection.session(self.timeout))
            self._failure = ""
        except DBusError as exc:
            self._connection = None
            self._failure = str(exc)
            self._next_attempt = time.monotonic() + RETRY_AFTER_SECONDS
        return self._connection

    @property
    def available(self) -> bool:
        return self.connection is not None

    @property
    def failure(self) -> str:
        self.connection  # noqa: B018 - refresh the reason
        return self._failure

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def fileno(self) -> int | None:
        connection = self.connection
        return connection.fileno() if connection else None

    def dispatch(self, timeout: float = 0.0) -> int:
        connection = self._connection
        if connection is None or connection.closed:
            return 0
        try:
            return connection.dispatch(timeout)
        except DBusError:
            return 0

    # -- questions ---------------------------------------------------------------------------
    def has_service(self, name: str, max_age: float = 5.0) -> bool:
        """Is anyone owning this well-known name right now?

        Cached briefly: a quick-settings panel asks about five services at once and none of them
        appears or disappears within a few seconds without also sending NameOwnerChanged.
        """
        cached = self._name_cache.get(name)
        now = time.monotonic()
        if cached and now - cached[0] < max_age:
            return cached[1]
        connection = self.connection
        if connection is None:
            return False
        try:
            owned = connection.name_has_owner(name)
        except DBusError:
            owned = False
        self._name_cache[name] = (now, owned)
        return owned

    def call(self, service: str, path: str, interface: str, member: str,
             signature: str = "", body: Iterable[Any] = (),
             timeout: float | None = None) -> Result:
        connection = self.connection
        source = f"{service}{path} {interface}.{member}"
        if connection is None:
            return Result.bad(self._failure or "no bus", source)
        message = Message(destination=service, path=path, interface=interface, member=member,
                          signature=signature, body=list(body))
        try:
            reply = connection.call(message, timeout if timeout is not None else self.timeout)
        except DBusError as exc:
            return Result.bad(str(exc), source)
        return Result.good(reply.body, source)

    def call_one(self, *args: Any, **kwargs: Any) -> Result:
        """`call` for the common case of a single return value."""
        result = self.call(*args, **kwargs)
        if not result.ok:
            return result
        values = result.value or []
        if len(values) != 1:
            return Result.bad(f"expected one value, got {len(values)}", result.source)
        return Result.good(values[0], result.source)

    # -- properties --------------------------------------------------------------------------
    def get(self, service: str, path: str, interface: str, name: str) -> Result:
        return self.call_one(service, path, catalog.PROPERTIES, "Get", "ss", [interface, name])

    def get_all(self, service: str, path: str, interface: str) -> Result:
        return self.call_one(service, path, catalog.PROPERTIES, "GetAll", "s", [interface])

    def set(self, service: str, path: str, interface: str, name: str,
            value: Variant) -> Result:
        if not isinstance(value, Variant):
            return Result.bad("a property is set with Variant(signature, value)")
        return self.call(service, path, catalog.PROPERTIES, "Set", "ssv",
                         [interface, name, value])

    def managed_objects(self, service: str, path: str) -> Result:
        """ObjectManager.GetManagedObjects — one call for a whole device tree.

        BlueZ, udisks2 and NetworkManager's settings all publish their inventory this way. Asking
        once beats walking Introspect() per object, which is what a slow tray does.
        """
        return self.call_one(service, path, catalog.OBJECT_MANAGER, "GetManagedObjects",
                             timeout=max(self.timeout, 10.0))

    # -- signals -----------------------------------------------------------------------------
    def on_signal(self, handler: Callable[[Message], None], **criteria: Any) -> Subscription | None:
        connection = self.connection
        if connection is None:
            return None
        try:
            return connection.subscribe(handler, **criteria)
        except DBusError:
            return None

    def on_properties_changed(self, handler: Callable[[str, dict, list, str], None], *,
                              sender: str | None = None, path: str | None = None,
                              path_namespace: str | None = None,
                              interface: str | None = None) -> Subscription | None:
        """Subscribe to PropertiesChanged and hand the handler its three decoded arguments.

        Signature is `sa{sv}as`: interface name, changed properties, invalidated property names.
        The fourth argument passed on is the object path, which is what tells two batteries apart.
        """
        def route(message: Message) -> None:
            body = list(message.body) + [None, None, None]
            changed_interface, changed, invalidated = body[0], body[1], body[2]
            if not isinstance(changed, dict):
                changed = {}
            if not isinstance(invalidated, list):
                invalidated = []
            handler(str(changed_interface), changed, invalidated, message.path or "")

        criteria: dict[str, Any] = {"interface": catalog.PROPERTIES,
                                    "member": "PropertiesChanged"}
        if sender:
            criteria["sender"] = sender
        if path:
            criteria["path"] = path
        if path_namespace:
            criteria["path_namespace"] = path_namespace
        if interface:
            criteria["arg0"] = interface       # PropertiesChanged's first argument is the interface
        return self.on_signal(route, **criteria)

    def on_objects_changed(self, added: Callable[[str, dict], None] | None = None,
                           removed: Callable[[str, list], None] | None = None, *,
                           sender: str | None = None,
                           path_namespace: str | None = None) -> list[Subscription]:
        """InterfacesAdded / InterfacesRemoved: hardware appearing and disappearing."""
        out: list[Subscription] = []
        if added is not None:
            def route_added(message: Message) -> None:
                body = list(message.body)
                if len(body) >= 2 and isinstance(body[1], dict):
                    added(str(body[0]), body[1])
            subscription = self.on_signal(route_added, interface=catalog.OBJECT_MANAGER,
                                          member="InterfacesAdded", sender=sender,
                                          path_namespace=path_namespace)
            if subscription:
                out.append(subscription)
        if removed is not None:
            def route_removed(message: Message) -> None:
                body = list(message.body)
                if len(body) >= 2 and isinstance(body[1], list):
                    removed(str(body[0]), body[1])
            subscription = self.on_signal(route_removed, interface=catalog.OBJECT_MANAGER,
                                          member="InterfacesRemoved", sender=sender,
                                          path_namespace=path_namespace)
            if subscription:
                out.append(subscription)
        return out


def decode_byte_string(value: Any) -> str:
    """udisks2 answers with NUL-terminated `ay` byte strings ("/dev/sda1\\0"). Make them text."""
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).rstrip(b"\0").decode("utf-8", "replace")
    if isinstance(value, list) and value and isinstance(value[0], int):
        return bytes(value).rstrip(b"\0").decode("utf-8", "replace")
    return str(value) if value is not None else ""
