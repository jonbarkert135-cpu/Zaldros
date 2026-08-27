"""Privacy — which applications may use the camera, the microphone and the location.

This is the portal permission store, the same database xdg-desktop-portal consults before it hands
a sandboxed application a camera stream [xdg-desktop-portal src/device.c and src/location.c,
1.18.4, 2026-08-28]. Writing "no" here really does stop the next request; it is not a preference
the shell keeps to itself.

What it cannot do is stop a *native, unsandboxed* program from opening `/dev/video0` directly.
The Settings page says that in one line rather than implying a guarantee the system does not make:
the switch governs portal requests, which is what Flatpak, Snap and every portal-using application
go through.
"""

from __future__ import annotations

from typing import Callable

from .bus import Bus, Result
from .catalog import PermissionStore
from .reading import NO_SERVICE, Reading
from .wire import Variant

# The three the Windows privacy page has and we can really answer for.
DEVICES = {"camera": (PermissionStore.DEVICES_TABLE, "camera"),
           "microphone": (PermissionStore.DEVICES_TABLE, "microphone"),
           "speakers": (PermissionStore.DEVICES_TABLE, "speakers"),
           "location": (PermissionStore.LOCATION_TABLE, PermissionStore.LOCATION_ID)}


class PermissionsFacet:
    def __init__(self, session_bus: Bus) -> None:
        self._bus = session_bus

    def available(self) -> bool:
        return self._bus.has_service(PermissionStore.SERVICE)

    # -- reading -----------------------------------------------------------------------------
    def device(self, device: str) -> Reading:
        """Every application's answer for one device, plus the summary the switch shows.

        The summary is deliberately pessimistic in the honest direction: the switch is *on* only
        when nothing is denied. An empty store means nothing has been asked yet, which is "on"
        with no applications listed — never a fabricated list.
        """
        if device not in DEVICES:
            return Reading.missing(NO_SERVICE, device)
        table, entry = DEVICES[device]
        result = self._bus.call(PermissionStore.SERVICE, PermissionStore.PATH,
                                PermissionStore.IFACE, "Lookup", "ss", [table, entry])
        if not result.ok:
            return Reading.missing(NO_SERVICE, PermissionStore.SERVICE)
        body = list(result.value or [])
        permissions = body[0] if body and isinstance(body[0], dict) else {}
        apps = {str(app): _first(values) for app, values in permissions.items()}
        denied = sorted(app for app, value in apps.items() if value == PermissionStore.NO)
        allowed = sorted(app for app, value in apps.items() if value == PermissionStore.YES)
        return Reading.measured(None, f"{len(allowed)} разрешено, {len(denied)} запрещено",
                                PermissionStore.PATH, table=table, entry=entry, apps=apps,
                                allowed=allowed, denied=denied, enabled=not denied)

    def app(self, device: str, app_id: str) -> Reading:
        reading = self.device(device)
        if not reading.available:
            return reading
        value = reading.get("apps", {}).get(app_id, "")
        return Reading.measured(None, value or PermissionStore.ASK, PermissionStore.PATH,
                                value=value or PermissionStore.ASK, app=app_id)

    # -- writing -----------------------------------------------------------------------------
    def set_app(self, device: str, app_id: str, allowed: bool | None) -> Result:
        """yes / no / ask for one application. `None` means ask again next time."""
        if device not in DEVICES:
            return Result.bad(f"unknown device {device!r}", PermissionStore.SERVICE)
        table, entry = DEVICES[device]
        value = (PermissionStore.ASK if allowed is None
                 else (PermissionStore.YES if allowed else PermissionStore.NO))
        return self._bus.call(PermissionStore.SERVICE, PermissionStore.PATH,
                              PermissionStore.IFACE, "SetPermission", "sbssas",
                              [table, True, entry, app_id, [value]])

    def set_device(self, device: str, allowed: bool) -> Result:
        """The page-level switch: applies to every application the store knows about.

        A store with no entries yet cannot be written blindly — there is no wildcard row in the
        portal database — so this reports that plainly instead of pretending the switch stuck.
        """
        reading = self.device(device)
        if not reading.available:
            return Result.bad("permission store is unavailable", PermissionStore.SERVICE)
        apps = reading.get("apps", {})
        if not apps:
            return Result.bad("no application has asked for this yet", PermissionStore.PATH)
        failures = []
        for app_id in apps:
            result = self.set_app(device, app_id, allowed)
            if not result.ok:
                failures.append(result.error)
        if failures:
            return Result.bad("; ".join(failures), PermissionStore.PATH)
        return Result.good(len(apps), PermissionStore.PATH)

    # -- change notification -------------------------------------------------------------------
    def watch(self, callback: Callable[[], None]) -> list:
        subscription = self._bus.on_signal(lambda _message: callback(),
                                           interface=PermissionStore.IFACE, member="Changed")
        return [subscription] if subscription else []


def _first(values: object) -> str:
    if isinstance(values, (list, tuple)) and values:
        return str(values[0])
    return ""
