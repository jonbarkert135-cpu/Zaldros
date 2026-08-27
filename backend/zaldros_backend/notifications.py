"""Notifications, both directions.

Zaldros needs to *send* them (a USB stick mounted, a battery at 5 %) and eventually to *be* the
server that receives them, because the Windows 11 notification centre is a shell surface, not a
separate daemon. The send side is complete and used; the receive side is the object below it,
which claims `org.freedesktop.Notifications` and hands every incoming notification to the shell.

Reference: Desktop Notifications Specification, latest
(https://specifications.freedesktop.org/notification/latest/), fetched 2026-08-27.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

from .bus import Bus, Result
from .catalog import Notifications as Spec
from .wire import METHOD_RETURN, Message, Variant

SERVER_NAME = "Zaldros"
SERVER_VENDOR = "Zaldros"
# Only what we really do. A capability we announce and do not honour is a lie other applications
# will act on: "body-markup" would make every notification arrive full of unrendered <b> tags.
CAPABILITIES = ["body", "actions", "persistence", "icon-static"]


@dataclass
class Notification:
    """One notification as the shell's centre shows it."""

    id: int
    app_name: str
    summary: str
    body: str
    icon: str = ""
    actions: list[str] = field(default_factory=list)
    urgency: int = Spec.URGENCY_NORMAL
    timeout_ms: int = -1
    transient: bool = False
    resident: bool = False
    desktop_entry: str = ""
    received_at: float = 0.0

    @property
    def critical(self) -> bool:
        return self.urgency == Spec.URGENCY_CRITICAL

    def action_pairs(self) -> list[tuple[str, str]]:
        """["default", "Открыть", "dismiss", "Скрыть"] -> [(key, label), ...]."""
        return [(self.actions[i], self.actions[i + 1])
                for i in range(0, len(self.actions) - 1, 2)]


class NotificationClient:
    """Sending. Used by the shell for its own messages."""

    def __init__(self, bus: Bus, app_name: str = SERVER_NAME) -> None:
        self._bus = bus
        self._app_name = app_name

    @property
    def available(self) -> bool:
        return self._bus.has_service(Spec.SERVICE)

    def notify(self, summary: str, body: str = "", *, icon: str = "", replaces: int = 0,
               actions: list[str] | None = None, urgency: int = Spec.URGENCY_NORMAL,
               timeout_ms: int = -1, transient: bool = False,
               desktop_entry: str = "") -> Result:
        hints: dict[str, Variant] = {"urgency": Variant("y", int(urgency))}
        if transient:
            hints["transient"] = Variant("b", True)
        if desktop_entry:
            hints["desktop-entry"] = Variant("s", desktop_entry)
        return self._bus.call_one(
            Spec.SERVICE, Spec.PATH, Spec.IFACE, "Notify", "susssasa{sv}i",
            [self._app_name, int(replaces), icon, summary, body, list(actions or []), hints,
             int(timeout_ms)])

    def close(self, notification_id: int) -> Result:
        return self._bus.call(Spec.SERVICE, Spec.PATH, Spec.IFACE, "CloseNotification", "u",
                              [int(notification_id)])

    def capabilities(self) -> list[str]:
        result = self._bus.call_one(Spec.SERVICE, Spec.PATH, Spec.IFACE, "GetCapabilities")
        return list(result.value) if result.ok and isinstance(result.value, list) else []


class NotificationServer:
    """Receiving: Zaldros itself as `org.freedesktop.Notifications`.

    Kept transport-shaped and Qt-free: `handle(message)` takes a parsed method call and returns
    the reply to send, so the whole protocol is testable without a bus, and the shell only has to
    own the socket. It does not draw anything — `on_notify` hands the parsed notification to the
    notification centre, which is a QML surface that already exists.
    """

    def __init__(self, on_notify: Callable[[Notification], None],
                 on_close: Callable[[int, int], None] | None = None,
                 clock: Callable[[], float] = time.time) -> None:
        self._on_notify = on_notify
        self._on_close = on_close
        self._clock = clock
        self._next_id = 1
        self.live: dict[int, Notification] = {}

    def claim(self, bus: Bus) -> Result:
        """Take the well-known name. Fails loudly when another daemon already holds it.

        Not `REPLACE_EXISTING`: if Plasma's own daemon is running in this session, silently
        stealing its name would break every notification in a way nobody could see.
        """
        connection = bus.connection
        if connection is None:
            return Result.bad(bus.failure or "no session bus", Spec.SERVICE)
        reply = bus.call_one("org.freedesktop.DBus", "/org/freedesktop/DBus",
                             "org.freedesktop.DBus", "RequestName", "su",
                             [Spec.SERVICE, 4])           # 4 = DO_NOT_QUEUE
        if not reply.ok:
            return reply
        # 1 = PRIMARY_OWNER, 3 = ALREADY_OWNER (both mean the name is ours)
        if int(reply.value) not in (1, 3):
            return Result.bad(f"{Spec.SERVICE} is already owned by another daemon", Spec.SERVICE)
        return Result.good(True, Spec.SERVICE)

    # -- protocol ----------------------------------------------------------------------------
    def handle(self, message: Message) -> Message | None:
        """Answer one incoming method call, or None when it is not ours to answer."""
        if message.interface != Spec.IFACE:
            return None
        if message.member == "GetCapabilities":
            return self._reply(message, "as", [CAPABILITIES])
        if message.member == "GetServerInformation":
            return self._reply(message, "ssss", [SERVER_NAME, SERVER_VENDOR, "1.0", "1.2"])
        if message.member == "Notify":
            return self._reply(message, "u", [self._notify(message.body)])
        if message.member == "CloseNotification":
            identifier = int(message.body[0]) if message.body else 0
            self.close(identifier, reason=3)
            return self._reply(message, "", [])
        return None

    def _notify(self, body: list[Any]) -> int:
        arguments = list(body) + [None] * (8 - len(body))
        app_name, replaces, icon, summary, text, actions, hints, timeout = arguments[:8]
        hints = hints if isinstance(hints, dict) else {}
        identifier = int(replaces or 0)
        if identifier <= 0:
            identifier = self._next_id
            self._next_id += 1
        notification = Notification(
            id=identifier, app_name=str(app_name or ""), summary=str(summary or ""),
            body=str(text or ""), icon=str(icon or ""),
            actions=[str(item) for item in (actions or [])],
            urgency=int(hints.get("urgency", Spec.URGENCY_NORMAL) or 0),
            timeout_ms=int(timeout if timeout is not None else -1),
            transient=bool(hints.get("transient", False)),
            resident=bool(hints.get("resident", False)),
            desktop_entry=str(hints.get("desktop-entry", "") or ""),
            received_at=self._clock())
        self.live[identifier] = notification
        self._on_notify(notification)
        return identifier

    def close(self, notification_id: int, reason: int = 2) -> Message | None:
        """Drop a notification and tell its sender why. Reasons are the spec's: 1 expired,
        2 dismissed by the user, 3 closed by a CloseNotification call, 4 undefined."""
        if notification_id not in self.live:
            return None
        del self.live[notification_id]
        if self._on_close is not None:
            self._on_close(notification_id, reason)
        return Message(type=4, path=Spec.PATH, interface=Spec.IFACE, member="NotificationClosed",
                       signature="uu", body=[int(notification_id), int(reason)])

    def action_invoked(self, notification_id: int, action_key: str) -> Message:
        return Message(type=4, path=Spec.PATH, interface=Spec.IFACE, member="ActionInvoked",
                       signature="us", body=[int(notification_id), action_key])

    @staticmethod
    def _reply(message: Message, signature: str, body: list[Any]) -> Message:
        return Message(type=METHOD_RETURN, reply_serial=message.serial,
                       destination=message.sender, signature=signature, body=body)
