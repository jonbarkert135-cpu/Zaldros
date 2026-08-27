"""`ZaldrosBackend` — the single object the UI is allowed to know about.

    Zaldros UI  ->  ZaldrosBackend  ->  Linux services

Before this existed the shell read /sys/class/power_supply itself, ran `wpctl`, ran `gdbus`, ran
`localectl`, and re-read all of it once a second from a QTimer. Every panel knew a different Linux
API and none of them knew when anything actually changed.

Two rules hold this together:

* **One entry point.** A panel asks `backend.power.battery()`; it never learns that the answer
  came from UPower's composite display device.
* **No polling.** Every facet subscribes to the signals its services already emit, the facade
  coalesces the burst, and the UI is told once. What cannot signal (audio) is refreshed when the
  surface that shows it opens, and that is written down rather than papered over with a timer.
"""

from __future__ import annotations

from typing import Callable

from . import hardware
from .accounts import AccountsFacet
from .audio import AudioFacet
from .bluetooth import BluetoothFacet
from .bus import Bus
from .defaultapps import DefaultAppsFacet
from .display import DisplayFacet
from .firewall import FirewallFacet
from .inputdevices import InputFacet
from .localetime import LocaleTimeFacet
from .network import NetworkFacet
from .notifications import NotificationClient, NotificationServer
from .permissions import PermissionsFacet
from .power import PowerFacet
from .reading import Reading
from .services import ServicesFacet
from .session import SessionFacet
from .storage import StorageFacet
from .updates import UpdatesFacet

DOMAINS = ("power", "network", "bluetooth", "audio", "storage", "display", "services",
           "session", "localetime", "input", "accounts", "permissions")


class ZaldrosBackend:
    """Everything the shell needs from the system, behind one door."""

    def __init__(self, system_bus: Bus | None = None, session_bus: Bus | None = None,
                 audio: AudioFacet | None = None) -> None:
        self.system_bus = system_bus if system_bus is not None else Bus("system")
        self.session_bus = session_bus if session_bus is not None else Bus("session")

        self.power = PowerFacet(self.system_bus)
        self.network = NetworkFacet(self.system_bus)
        self.bluetooth = BluetoothFacet(self.system_bus)
        self.audio = audio if audio is not None else AudioFacet()
        self.storage = StorageFacet(self.system_bus)
        self.display = DisplayFacet(self.session_bus)
        self.services = ServicesFacet(self.system_bus, self.session_bus)
        self.session = SessionFacet(self.system_bus, self.session_bus)
        self.notify = NotificationClient(self.session_bus)
        self.hardware = hardware

        # The facets Settings needs beyond the tray: they are constructed here too, because a
        # second construction site is a second place to get a bus wrong.
        self.localetime = LocaleTimeFacet(self.system_bus)
        self.input = InputFacet(self.session_bus)
        self.accounts = AccountsFacet(self.system_bus, self.session)
        self.permissions = PermissionsFacet(self.session_bus)
        self.firewall = FirewallFacet(self.system_bus)
        self.updates = UpdatesFacet(self.system_bus)
        self.apps = DefaultAppsFacet()

        self._listeners: dict[str, list[Callable[[], None]]] = {name: [] for name in DOMAINS}
        self._watching: dict[str, list] = {}
        self._dirty: set[str] = set()

    # -- authorisation is built on the same system bus ----------------------------------------
    @property
    def auth(self):
        from .auth import AuthFacet
        if not hasattr(self, "_auth"):
            self._auth = AuthFacet(self.system_bus)
        return self._auth

    def notification_server(self, on_notify, on_close=None) -> NotificationServer:
        return NotificationServer(on_notify, on_close)

    # -- change notification -------------------------------------------------------------------
    def subscribe(self, domain: str, callback: Callable[[], None]) -> None:
        """Be told when `domain` changed. The first subscriber installs the match rules.

        Subscribing is what turns a service on: a session that never opens quick settings never
        asks BlueZ anything and never receives a single BlueZ signal.
        """
        if domain not in self._listeners:
            raise ValueError(f"unknown domain {domain!r}; known: {', '.join(DOMAINS)}")
        self._listeners[domain].append(callback)
        if domain not in self._watching:
            self._watching[domain] = self._install(domain)

    def _install(self, domain: str) -> list:
        mark = lambda: self._dirty.add(domain)   # noqa: E731 - a one-liner is the whole point
        facet = getattr(self, domain, None)
        if domain == "session":
            return (self.session.watch_layout(mark)
                    + self.session.watch_lock(mark, mark))
        if facet is not None and hasattr(facet, "watch"):
            return facet.watch(mark)
        return []

    def dispatch(self, timeout: float = 0.0) -> int:
        """Read whatever the buses have to say. Returns how many signals arrived."""
        return self.system_bus.dispatch(timeout) + self.session_bus.dispatch(timeout)

    def flush(self) -> list[str]:
        """Tell the listeners of every domain that changed since the last flush, once each.

        The coalescing is the point. NetworkManager emits a dozen PropertiesChanged while a Wi-Fi
        association completes; without this the tray would rebuild itself a dozen times in 200 ms.
        """
        changed = sorted(self._dirty)
        self._dirty.clear()
        for domain in changed:
            for callback in list(self._listeners[domain]):
                callback()
        return changed

    def invalidate(self, domain: str) -> None:
        """Mark a domain changed by hand — used after our own write (a slider, a toggle)."""
        if domain in self._listeners:
            self._dirty.add(domain)

    @property
    def pending(self) -> set[str]:
        return set(self._dirty)

    # -- what the tray shows ---------------------------------------------------------------------
    def tray(self) -> dict[str, Reading]:
        """Every reading the taskbar and quick settings draw, in one call.

        Deliberately a single method: the tray is drawn as one row, so it should be read as one
        row, and any facet that is slow shows up here rather than in six separate places.
        """
        return {
            "battery": self.power.battery(),
            "network": self.network.status(),
            "volume": self.audio.volume(),
            "bluetooth": self.bluetooth.adapter(),
            "brightness": self.display.brightness(),
            "keyboard": self.session.keyboard_layout(),
        }

    # -- diagnostics -------------------------------------------------------------------------
    def status(self) -> dict[str, object]:
        """What the backend is actually connected to. For the boot report, not for the UI."""
        return {
            "system_bus": self.system_bus.available,
            "system_bus_error": self.system_bus.failure,
            "session_bus": self.session_bus.available,
            "session_bus_error": self.session_bus.failure,
            "audio_tool": self.audio.tool(),
            "watching": {domain: len(subs) for domain, subs in self._watching.items()},
            "match_rules": sum(len(subs) for subs in self._watching.values()),
            "listeners": {domain: len(callbacks) for domain, callbacks in self._listeners.items()
                          if callbacks},
        }

    def close(self) -> None:
        self.system_bus.close()
        self.session_bus.close()
