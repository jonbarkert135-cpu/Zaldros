"""Services: systemd, for the Settings «Службы» page and for Zaldros's own units.

Two managers, not one: the system manager runs NetworkManager and bluetooth, the user manager runs
the shell's own session units. A page that only knows the system bus cannot see half of what is
running on a modern desktop.
"""

from __future__ import annotations

from typing import Callable

from .bus import Bus, Result
from .catalog import Systemd
from .reading import NO_SERVICE, Reading

ACTIVE_TEXT = {"active": "работает", "inactive": "остановлена", "failed": "сбой",
               "activating": "запускается", "deactivating": "останавливается",
               "reloading": "перезагружает конфигурацию"}


class ServicesFacet:
    """One facet over both systemd managers. `scope` is "system" or "user"."""

    def __init__(self, system_bus: Bus, session_bus: Bus) -> None:
        self._buses = {"system": system_bus, "user": session_bus}

    def _bus(self, scope: str) -> Bus:
        if scope not in self._buses:
            raise ValueError(f"scope is 'system' or 'user', not {scope!r}")
        return self._buses[scope]

    def units(self, scope: str = "system", suffix: str = ".service",
              loaded_only: bool = True) -> list[Reading]:
        """The unit list, as `systemctl list-units` shows it.

        `value` is None throughout: a unit has a state, not a number, and the honesty contract
        says an absent number stays absent rather than being encoded as 0 or 1.
        """
        listed = self._bus(scope).call_one(Systemd.SERVICE, Systemd.PATH, Systemd.MANAGER,
                                           "ListUnits", timeout=15.0)
        if not listed.ok:
            return []
        out: list[Reading] = []
        for row in listed.value or []:
            if len(row) < len(Systemd.LIST_UNITS_SIGNATURE):
                continue
            unit = dict(zip(Systemd.LIST_UNITS_SIGNATURE, row))
            name = str(unit["name"])
            if suffix and not name.endswith(suffix):
                continue
            if loaded_only and unit["load_state"] != "loaded":
                continue
            active = str(unit["active_state"])
            out.append(Reading.measured(
                None, str(unit["description"]) or name, f"{scope}:{name}",
                unit=name, active=active, sub=str(unit["sub_state"]),
                running=active == "active", failed=active == "failed",
                state_text=ACTIVE_TEXT.get(active, active), scope=scope,
                path=str(unit["path"])))
        return sorted(out, key=lambda item: item.get("unit", ""))

    def unit(self, name: str, scope: str = "system") -> Reading:
        path = self._bus(scope).call_one(Systemd.SERVICE, Systemd.PATH, Systemd.MANAGER,
                                         "GetUnit", "s", [name])
        if not path.ok:
            return Reading.missing(NO_SERVICE, f"{scope}:{name}")
        values = self._bus(scope).get_all(Systemd.SERVICE, str(path.value), Systemd.UNIT)
        if not values.ok:
            return Reading.missing(NO_SERVICE, f"{scope}:{name}")
        active = str(values.value.get("ActiveState", "unknown"))
        return Reading.measured(None, str(values.value.get("Description", name)),
                                f"{scope}:{name}", unit=name, active=active,
                                sub=str(values.value.get("SubState", "")),
                                running=active == "active", failed=active == "failed",
                                state_text=ACTIVE_TEXT.get(active, active), scope=scope,
                                path=str(path.value))

    def failed(self, scope: str = "system") -> list[Reading]:
        """What is broken right now — the only service list a normal user should ever be shown."""
        return [unit for unit in self.units(scope) if unit.get("failed")]

    def start(self, name: str, scope: str = "system") -> Result:
        return self._act("StartUnit", name, scope)

    def stop(self, name: str, scope: str = "system") -> Result:
        return self._act("StopUnit", name, scope)

    def restart(self, name: str, scope: str = "system") -> Result:
        return self._act("RestartUnit", name, scope)

    def _act(self, method: str, name: str, scope: str) -> Result:
        return self._bus(scope).call(Systemd.SERVICE, Systemd.PATH, Systemd.MANAGER, method,
                                     "ss", [name, Systemd.REPLACE], timeout=25.0)

    def watch(self, callback: Callable[[], None], scope: str = "system") -> list:
        """systemd only emits unit signals to clients that asked for them.

        `Subscribe()` is not optional here: without it the manager stays silent and a services
        page would look frozen. It is reference-counted per connection, so calling it twice is
        harmless.
        """
        bus = self._bus(scope)
        bus.call(Systemd.SERVICE, Systemd.PATH, Systemd.MANAGER, "Subscribe")
        subscriptions = []
        for member in ("UnitNew", "UnitRemoved", "JobRemoved"):
            subscription = bus.on_signal(lambda _message: callback(), interface=Systemd.MANAGER,
                                         member=member)
            if subscription:
                subscriptions.append(subscription)
        return subscriptions
