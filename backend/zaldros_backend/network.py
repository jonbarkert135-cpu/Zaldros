"""Network: NetworkManager, reduced to what a Windows-shaped tray shows.

The taskbar needs four things — am I online, over what, how strong, and what is it called — and
quick settings needs a Wi-Fi list and a toggle. NetworkManager can answer all of it; the UI never
learns the words "ActiveConnection" or "AccessPoint".
"""

from __future__ import annotations

from typing import Any, Callable

from .bus import Bus, Result
from .catalog import NetworkManager as NM
from .reading import NO_DATA, NO_SERVICE, Reading

CONNECTIVITY_TEXT = {
    "full": "подключено", "limited": "без доступа к интернету",
    "portal": "требуется вход в сеть", "none": "нет подключения",
    "unknown": "состояние неизвестно",
}
KIND_TEXT = {"wifi": "Wi-Fi", "ethernet": "Ethernet", "modem": "мобильная сеть",
             "bluetooth": "Bluetooth"}


class NetworkFacet:
    def __init__(self, bus: Bus, sysfs_root: str = "/sys/class/net") -> None:
        self._bus = bus
        self._sysfs_root = sysfs_root

    # -- what the tray shows -----------------------------------------------------------------
    def status(self) -> Reading:
        """One line for the tray: the primary connection, its kind and its signal.

        `Strength` only exists on Wi-Fi. On Ethernet the value stays None and the UI draws the
        wired glyph — a fabricated "100 %" on a cable would be a lie with a plausible face.
        """
        if not self._bus.has_service(NM.SERVICE):
            return self._sysfs_status()
        manager = self._bus.get_all(NM.SERVICE, NM.PATH, NM.IFACE)
        if not manager.ok:
            return self._sysfs_status()
        values = manager.value
        state = NM.STATE.get(int(values.get("State", 0) or 0), "unknown")
        connectivity = NM.CONNECTIVITY.get(int(values.get("Connectivity", 0) or 0), "unknown")
        primary = values.get("PrimaryConnection") or ""
        if state not in ("connected", "connected-site", "connected-local") or primary in ("", "/"):
            return Reading.missing(CONNECTIVITY_TEXT.get(connectivity, "нет подключения"),
                                   NM.PATH)
        name, kind, device_path = self._primary_details(str(primary),
                                                        str(values.get("PrimaryConnectionType", "")))
        strength = self._strength(device_path) if kind == "wifi" else None
        detail = name or KIND_TEXT.get(kind, kind)
        if connectivity in ("limited", "portal", "none"):
            detail = f"{detail} · {CONNECTIVITY_TEXT[connectivity]}"
        metered = NM.METERED.get(int(values.get("Metered", 0) or 0), "unknown")
        return Reading.measured(strength, detail, NM.PATH, kind=kind, name=name,
                                connectivity=connectivity, state=state,
                                metered=metered in ("yes", "guess-yes"),
                                wifi_enabled=bool(values.get("WirelessEnabled", False)),
                                device=device_path)

    def _sysfs_status(self) -> Reading:
        """/sys/class/net, for a session with no NetworkManager (a server image, a rescue shell).

        It can answer one question honestly — is an interface up, and is it wireless — and no
        more: there is no SSID and no signal strength in sysfs, so neither is invented.
        """
        from pathlib import Path
        try:
            interfaces = sorted(path for path in Path(self._sysfs_root).iterdir()
                                if path.name != "lo")
        except OSError:
            return Reading.missing(NO_DATA, self._sysfs_root)
        for path in interfaces:
            try:
                state = (path / "operstate").read_text().strip()
            except OSError:
                continue
            if state != "up":
                continue
            wireless = (path / "wireless").exists()
            return Reading.measured(None, f"{path.name} · {'Wi-Fi' if wireless else 'Ethernet'}",
                                    str(path), kind="wifi" if wireless else "ethernet",
                                    name=path.name, connectivity="unknown", state="connected",
                                    metered=False, wifi_enabled=wireless, device="")
        return Reading.missing("нет подключения", self._sysfs_root)

    def _primary_details(self, active_path: str, type_hint: str) -> tuple[str, str, str]:
        active = self._bus.get_all(NM.SERVICE, active_path, NM.ACTIVE_CONNECTION)
        name = ""
        kind = _kind_from_type(type_hint)
        device_path = ""
        if active.ok:
            name = str(active.value.get("Id", "") or "")
            devices = active.value.get("Devices") or []
            if devices:
                device_path = str(devices[0])
        if device_path:
            device_type = self._bus.get(NM.SERVICE, device_path, NM.DEVICE, "DeviceType")
            if device_type.ok:
                kind = NM.DEVICE_TYPE.get(int(device_type.value or 0), kind)
        return name, kind, device_path

    def _strength(self, device_path: str) -> int | None:
        if not device_path:
            return None
        access_point = self._bus.get(NM.SERVICE, device_path, NM.WIRELESS, "ActiveAccessPoint")
        if not access_point.ok or str(access_point.value) in ("", "/"):
            return None
        strength = self._bus.get(NM.SERVICE, str(access_point.value), NM.ACCESS_POINT, "Strength")
        return int(strength.value) if strength.ok and strength.value is not None else None

    # -- devices and access points -----------------------------------------------------------
    def devices(self) -> list[Reading]:
        listed = self._bus.call_one(NM.SERVICE, NM.PATH, NM.IFACE, "GetDevices")
        if not listed.ok:
            return []
        out: list[Reading] = []
        for path in listed.value or []:
            properties = self._bus.get_all(NM.SERVICE, path, NM.DEVICE)
            if not properties.ok:
                continue
            values = properties.value
            kind = NM.DEVICE_TYPE.get(int(values.get("DeviceType", 0) or 0), "other")
            if kind in ("loopback", "other"):
                continue
            state = NM.DEVICE_STATE.get(int(values.get("State", 0) or 0), "unknown")
            out.append(Reading.measured(None, str(values.get("Interface", "")), path, kind=kind,
                                        state=state, connected=state == "activated",
                                        driver=str(values.get("Driver", "")),
                                        hw_address=str(values.get("HwAddress", ""))))
        return out

    def access_points(self, device_path: str | None = None) -> list[Reading]:
        """The Wi-Fi list, sorted the way Windows sorts it: strongest first, one entry per SSID.

        NetworkManager publishes one AccessPoint object per BSSID, so a mesh network appears three
        times. The panel shows networks, not radios.
        """
        device = device_path or self._wifi_device()
        if not device:
            return []
        listed = self._bus.call_one(NM.SERVICE, device, NM.WIRELESS, "GetAllAccessPoints")
        if not listed.ok:
            return []
        active = self._bus.get(NM.SERVICE, device, NM.WIRELESS, "ActiveAccessPoint")
        active_path = str(active.value) if active.ok else ""
        best: dict[str, Reading] = {}
        for path in listed.value or []:
            properties = self._bus.get_all(NM.SERVICE, path, NM.ACCESS_POINT)
            if not properties.ok:
                continue
            values = properties.value
            ssid = _decode_ssid(values.get("Ssid"))
            if not ssid:
                continue
            strength = int(values.get("Strength", 0) or 0)
            secured = bool(int(values.get("Flags", 0) or 0) & NM.AP_FLAG_PRIVACY
                           or int(values.get("WpaFlags", 0) or 0)
                           or int(values.get("RsnFlags", 0) or 0))
            reading = Reading.measured(strength, ssid, path, ssid=ssid, secured=secured,
                                       active=path == active_path,
                                       frequency=int(values.get("Frequency", 0) or 0))
            previous = best.get(ssid)
            if previous is None or strength > (previous.value or 0) or reading.get("active"):
                best[ssid] = reading
        return sorted(best.values(), key=lambda item: (not item.get("active"), -(item.value or 0)))

    def _wifi_device(self) -> str:
        for device in self.devices():
            if device.get("kind") == "wifi":
                return device.source
        return ""

    def request_scan(self) -> Result:
        device = self._wifi_device()
        if not device:
            return Result.bad("no Wi-Fi device", NM.SERVICE)
        return self._bus.call(NM.SERVICE, device, NM.WIRELESS, "RequestScan", "a{sv}", [{}])

    # -- toggles -----------------------------------------------------------------------------
    def wifi_enabled(self) -> Reading:
        value = self._bus.get(NM.SERVICE, NM.PATH, NM.IFACE, "WirelessEnabled")
        if not value.ok:
            return Reading.missing(NO_SERVICE, value.source)
        hardware = self._bus.get(NM.SERVICE, NM.PATH, NM.IFACE, "WirelessHardwareEnabled")
        blocked = hardware.ok and not hardware.value
        return Reading.measured(1 if value.value else 0,
                                "аппаратно выключен" if blocked else "", value.source,
                                enabled=bool(value.value), hardware_blocked=blocked)

    def networking_enabled(self) -> Reading:
        """The master switch: NetworkManager.NetworkingEnabled. Off means every interface is
        down, which is a different fact from "Wi-Fi is off"."""
        value = self._bus.get(NM.SERVICE, NM.PATH, NM.IFACE, "NetworkingEnabled")
        if not value.ok:
            return Reading.missing(NO_SERVICE, value.source)
        return Reading.measured(1 if value.value else 0, "", value.source,
                                enabled=bool(value.value))

    def set_wifi_enabled(self, enabled: bool) -> Result:
        from .wire import Variant
        return self._bus.set(NM.SERVICE, NM.PATH, NM.IFACE, "WirelessEnabled",
                             Variant("b", bool(enabled)))

    def set_networking_enabled(self, enabled: bool) -> Result:
        """Airplane mode's real switch: NetworkManager.Enable(b)."""
        return self._bus.call(NM.SERVICE, NM.PATH, NM.IFACE, "Enable", "b", [bool(enabled)])

    def activate(self, connection_path: str, device_path: str = "/") -> Result:
        return self._bus.call(NM.SERVICE, NM.PATH, NM.IFACE, "ActivateConnection", "ooo",
                              [connection_path, device_path, "/"])

    # -- change notification -----------------------------------------------------------------
    def watch(self, callback: Callable[[], None]) -> list:
        """One match rule for the whole NetworkManager tree.

        `path_namespace` is what makes this cheap: devices and access points come and go
        constantly, and re-subscribing per object on every scan would cost more than the polling
        it replaces.
        """
        subscriptions = []
        properties = self._bus.on_properties_changed(lambda *_args: callback(),
                                                     path_namespace=NM.NAMESPACE)
        if properties:
            subscriptions.append(properties)
        state = self._bus.on_signal(lambda _message: callback(), interface=NM.IFACE,
                                    member="StateChanged")
        if state:
            subscriptions.append(state)
        return subscriptions


def _kind_from_type(type_name: str) -> str:
    if type_name.startswith("802-11"):
        return "wifi"
    if type_name.startswith("802-3"):
        return "ethernet"
    if type_name in ("gsm", "cdma"):
        return "modem"
    return type_name or "unknown"


def _decode_ssid(value: Any) -> str:
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).decode("utf-8", "replace").strip("\0")
    if isinstance(value, list) and value and isinstance(value[0], int):
        return bytes(value).decode("utf-8", "replace").strip("\0")
    return str(value or "")
