"""User accounts — accountsservice.

Windows' "Учётные записи" page lists the people who can log in, says which of them is an
administrator, and can turn automatic login on. All three are accountsservice's job on Linux;
`/etc/passwd` is not, because reading it would show forty system accounts and could not change
anything.

Creating and deleting users is intentionally *not* exposed yet: both need a polkit prompt and a
confirmation flow that the Settings page does not have, and a half-built delete button is the one
button in a settings app that must not be half-built.
"""

from __future__ import annotations

from typing import Callable

from .bus import Bus, Result
from .catalog import Accounts
from .reading import NO_SERVICE, Reading
from .session import SessionFacet


class AccountsFacet:
    def __init__(self, system_bus: Bus, session: SessionFacet | None = None) -> None:
        self._bus = system_bus
        self._session = session

    def available(self) -> bool:
        return self._bus.has_service(Accounts.SERVICE)

    # -- reading -----------------------------------------------------------------------------
    def users(self) -> list[Reading]:
        """Every human account the daemon caches, current session first."""
        paths = self._bus.call_one(Accounts.SERVICE, Accounts.PATH, Accounts.IFACE,
                                   "ListCachedUsers")
        if not paths.ok or not isinstance(paths.value, list):
            return []
        current = self._session.user_name() if self._session else ""
        out = [reading for reading in (self._user_at(str(path)) for path in paths.value)
               if reading is not None]
        out.sort(key=lambda reading: (reading.get("name") != current, reading.get("name", "")))
        return out

    def user(self, name: str) -> Reading:
        path = self._bus.call_one(Accounts.SERVICE, Accounts.PATH, Accounts.IFACE,
                                  "FindUserByName", "s", [name])
        if not path.ok:
            return Reading.missing(NO_SERVICE, Accounts.SERVICE)
        reading = self._user_at(str(path.value))
        return reading if reading is not None else Reading.missing(NO_SERVICE, str(path.value))

    def _user_at(self, path: str) -> Reading | None:
        values = self._bus.get_all(Accounts.SERVICE, path, Accounts.USER)
        if not values.ok or not isinstance(values.value, dict) or not values.value:
            return None
        data = values.value
        if bool(data.get("SystemAccount", False)):
            return None
        kind = int(data.get("AccountType", 0) or 0)
        return Reading.measured(
            None, str(data.get("RealName") or data.get("UserName", "")), path,
            name=str(data.get("UserName", "")), real_name=str(data.get("RealName", "")),
            uid=int(data.get("Uid", 0) or 0), path=path,
            admin=kind == 1, kind=Accounts.ACCOUNT_TYPE.get(kind, str(kind)),
            locked=bool(data.get("Locked", False)),
            automatic_login=bool(data.get("AutomaticLogin", False)),
            home=str(data.get("HomeDirectory", "")), shell=str(data.get("Shell", "")))

    def automatic_login(self) -> Reading:
        """Whether *anyone* logs in without a password, and who. One switch, one answer."""
        users = self.users()
        if not users:
            return Reading.missing(NO_SERVICE, Accounts.SERVICE)
        chosen = [user for user in users if user.get("automatic_login")]
        return Reading.measured(None, chosen[0].get("name", "") if chosen else "",
                                Accounts.PATH, enabled=bool(chosen),
                                user=chosen[0].get("name", "") if chosen else "")

    # -- writing -----------------------------------------------------------------------------
    def set_automatic_login(self, name: str, enabled: bool) -> Result:
        user = self.user(name)
        if not user.available:
            return Result.bad(f"no account {name!r}", Accounts.SERVICE)
        return self._bus.call(Accounts.SERVICE, user.get("path", ""), Accounts.USER,
                              "SetAutomaticLogin", "b", [bool(enabled)], timeout=30.0)

    def set_admin(self, name: str, admin: bool) -> Result:
        user = self.user(name)
        if not user.available:
            return Result.bad(f"no account {name!r}", Accounts.SERVICE)
        return self._bus.call(Accounts.SERVICE, user.get("path", ""), Accounts.USER,
                              "SetAccountType", "i", [1 if admin else 0], timeout=30.0)

    def set_locked(self, name: str, locked: bool) -> Result:
        user = self.user(name)
        if not user.available:
            return Result.bad(f"no account {name!r}", Accounts.SERVICE)
        return self._bus.call(Accounts.SERVICE, user.get("path", ""), Accounts.USER,
                              "SetLocked", "b", [bool(locked)], timeout=30.0)

    def set_real_name(self, name: str, real_name: str) -> Result:
        user = self.user(name)
        if not user.available:
            return Result.bad(f"no account {name!r}", Accounts.SERVICE)
        return self._bus.call(Accounts.SERVICE, user.get("path", ""), Accounts.USER,
                              "SetRealName", "s", [real_name], timeout=30.0)

    # -- change notification -------------------------------------------------------------------
    def watch(self, callback: Callable[[], None]) -> list:
        subscription = self._bus.on_properties_changed(lambda *_args: callback(),
                                                       interface=Accounts.USER)
        return [subscription] if subscription else []
