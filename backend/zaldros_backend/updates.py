# SPDX-License-Identifier: GPL-3.0-or-later
"""System updates — PackageKit.

PackageKit is the one API that answers "what would be updated" without knowing whether the machine
underneath runs apt, dnf or something else, and it is what Ubuntu already runs for unattended
upgrades.

Its shape is unusual and this facet does not hide it: you ask the daemon for a transaction object,
call a method on it, and the *answers arrive as signals* until `Finished`. So a query here is a
short pump of the bus with a deadline, and if the deadline passes the reading says the daemon did
not finish — never an empty list, which would read as "you are up to date".
"""

from __future__ import annotations

import time
from typing import Any, Callable

from .bus import Bus, Result
from .catalog import PackageKit
from .reading import NO_SERVICE, Reading

NO_DAEMON = "служба обновлений недоступна"
TIMED_OUT = "служба обновлений не ответила"


class UpdatesFacet:
    def __init__(self, system_bus: Bus) -> None:
        self._bus = system_bus

    def available(self) -> bool:
        return self._bus.has_service(PackageKit.SERVICE)

    def daemon(self) -> Reading:
        values = self._bus.get_all(PackageKit.SERVICE, PackageKit.PATH, PackageKit.IFACE)
        if not values.ok or not isinstance(values.value, dict) or not values.value:
            return Reading.missing(NO_DAEMON, PackageKit.SERVICE)
        data = values.value
        version = ".".join(str(int(data.get(f"Version{part}", 0) or 0))
                           for part in ("Major", "Minor", "Micro"))
        return Reading.measured(None, str(data.get("BackendName", "")), PackageKit.PATH,
                                backend=str(data.get("BackendName", "")),
                                distro=str(data.get("DistroId", "")), version=version,
                                network=int(data.get("NetworkState", 0) or 0),
                                locked=bool(data.get("Locked", False)))

    # -- queries -----------------------------------------------------------------------------
    def updates(self, timeout: float = 60.0,
                cancelled: Callable[[], bool] | None = None) -> Reading:
        """The packages that would be installed, counted and named.

        `value` is the number of updates, so the Settings row can show a number; `packages` holds
        `(info, package_id, summary)` for the detail page. A failure is a failure: the caller can
        tell "0 updates" from "we could not ask".
        """
        collected: list[dict[str, str]] = []
        outcome = self._transaction("GetUpdates", "t", [PackageKit.FILTER_NONE], collected,
                                    timeout, cancelled)
        if not outcome.ok:
            return Reading.missing(outcome.error or NO_SERVICE, PackageKit.SERVICE)
        security = sum(1 for package in collected if package["info"] == "security")
        return Reading.measured(len(collected), _summary(len(collected), security),
                                PackageKit.SERVICE, packages=collected, security=security)

    def refresh(self, timeout: float = 180.0,
                cancelled: Callable[[], bool] | None = None) -> Result:
        """Re-read the repositories, the way "Проверить обновления" does in Windows."""
        return self._transaction("RefreshCache", "b", [False], [], timeout, cancelled)

    # -- the transaction dance -----------------------------------------------------------------
    def _transaction(self, member: str, signature: str, body: list[Any],
                     collected: list[dict[str, str]], timeout: float,
                     cancelled: Callable[[], bool] | None = None) -> Result:
        deadline = time.monotonic() + timeout

        def stopped() -> bool:
            return time.monotonic() >= deadline or bool(cancelled and cancelled())

        def ask(service, path, interface, method, signature="", values=(), one=False):
            if stopped():
                return Result.bad(TIMED_OUT, path)
            call = self._bus.call_one if one else self._bus.call
            return call(service, path, interface, method, signature, values,
                        timeout=max(0.001, deadline - time.monotonic()), cancelled=stopped)

        # A well-known destination lets the daemon activate an installed service.
        # The reply's sender identifies the process that actually created this
        # transaction, rather than a possibly stale GetNameOwner snapshot.
        created = ask(PackageKit.SERVICE, PackageKit.PATH, PackageKit.IFACE,
                      "CreateTransaction", one=True)
        if not created.ok:
            return Result.bad(created.error or NO_DAEMON, PackageKit.SERVICE)
        owner = created.reply_sender
        if not owner.startswith(":"):
            return Result.bad(NO_DAEMON, PackageKit.SERVICE)
        connection = self._bus.connection
        path = str(created.value)
        finished: dict[str, Any] = {}

        def on_package(message) -> None:
            values = list(message.body)
            if len(values) >= 3:
                collected.append({"info": PackageKit.INFO.get(int(values[0]), str(values[0])),
                                  "id": str(values[1]), "summary": str(values[2])})

        def on_finished(message) -> None:
            values = list(message.body)
            finished["exit"] = PackageKit.EXIT.get(int(values[0]) if values else 0, "unknown")

        def on_error(message) -> None:
            values = list(message.body)
            finished["error"] = str(values[1]) if len(values) > 1 else "error"

        def on_owner(message) -> None:
            if len(message.body) == 3 and message.body[1] == owner:
                finished["error"] = NO_DAEMON

        subscriptions = [
            self._bus.on_signal(on_package, path=path, interface=PackageKit.TRANSACTION,
                                member="Package", sender=owner),
            self._bus.on_signal(on_finished, path=path, interface=PackageKit.TRANSACTION,
                                member="Finished", sender=owner),
            self._bus.on_signal(on_error, path=path, interface=PackageKit.TRANSACTION,
                                member="ErrorCode", sender=owner),
            self._bus.on_signal(on_owner, sender="org.freedesktop.DBus",
                                path="/org/freedesktop/DBus", interface="org.freedesktop.DBus",
                                member="NameOwnerChanged", arg0=PackageKit.SERVICE)]
        try:
            if any(subscription is None for subscription in subscriptions):
                return Result.bad("could not subscribe to update transaction", path)
            # Subscribe first, then verify ownership: a loss between the create
            # reply and installing NameOwnerChanged must not be silently missed.
            current = ask("org.freedesktop.DBus", "/org/freedesktop/DBus",
                          "org.freedesktop.DBus", "GetNameOwner", "s", [PackageKit.SERVICE], one=True)
            if not current.ok or current.value != owner:
                return Result.bad(NO_DAEMON, path)
            call = ask(owner, path, PackageKit.TRANSACTION, member, signature, body)
            if not call.ok:
                return Result.bad(call.error, path)
            while "exit" not in finished and "error" not in finished:
                if stopped():
                    return Result.bad(TIMED_OUT, path)
                if connection is None or connection.closed:
                    return Result.bad(NO_DAEMON, path)
                self._bus.dispatch(0.05)
        finally:
            for subscription in subscriptions:
                if subscription is not None:
                    subscription.cancel()
        if "error" in finished:
            return Result.bad(str(finished["error"]), path)
        if finished.get("exit") != "success":
            return Result.bad(f"PackageKit finished with {finished.get('exit')}", path)
        return Result.good(True, path)


def _summary(total: int, security: int) -> str:
    if total == 0:
        return "обновлений нет"
    if security:
        return f"{total} обновлений, из них {security} по безопасности"
    return f"{total} обновлений"
