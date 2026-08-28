"""Zaldros Backend — one layer between the Zaldros UI and the Linux services under it.

    Zaldros UI  ->  Zaldros Backend  ->  systemd, NetworkManager, PipeWire, BlueZ, UPower,
                                         udisks2, polkit, logind, KWin

Why it exists: without it every panel learns a different Linux API, every panel invents its own
answer for "this machine has no battery", and everything gets re-read on a timer because nobody
subscribed to anything. See `../README.md` and `docs/state/decisions/ADR-0014`.

Nothing here imports Qt except `qtbridge`, so the backend is testable — and usable — without a UI.

    from zaldros_backend import ZaldrosBackend
    backend = ZaldrosBackend()
    print(backend.power.battery().percent)
"""

from .bus import Bus, Result
from .connection import Connection, DBusError
from .facade import DOMAINS, ZaldrosBackend
from .devices import Device, DevicesFacet
from .processes import Process, ProcessFacet, Sampler, Snapshot
from .notifications import Notification, NotificationServer, policy_from
from .reading import NO_DATA, NO_SERVICE, NOT_PRESENT, NOT_SUPPORTED, Reading
from .wire import Message, Variant

__all__ = ["Bus", "Connection", "DBusError", "DOMAINS", "Message", "Notification",
           "NotificationServer", "policy_from", "Device", "DevicesFacet", "Process", "ProcessFacet", "Sampler", "Snapshot", "Reading", "Result", "Variant", "ZaldrosBackend",
           "NO_DATA", "NO_SERVICE", "NOT_PRESENT", "NOT_SUPPORTED"]
