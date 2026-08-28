"""Bluetooth: BlueZ through its object manager.

BlueZ has no "list devices" method — the inventory *is* the object tree. One
`GetManagedObjects()` gives every adapter, every known device and every battery in a single round
trip; `InterfacesAdded` / `InterfacesRemoved` keep it current without asking again.
"""

from __future__ import annotations

from typing import Any, Callable

from .bus import Bus, Result
from .catalog import BlueZ
from .reading import NO_SERVICE, NOT_PRESENT, Reading

# Verbatim from the shell as it renders today (visual gate).
ADAPTER_ABSENT = "адаптер не найден"
from .wire import Variant


class BluetoothFacet:
    def __init__(self, bus: Bus, sysfs_root: str = "/sys/class/bluetooth") -> None:
        self._bus = bus
        self._sysfs_root = sysfs_root

    def _tree(self) -> dict[str, dict[str, dict[str, Any]]]:
        result = self._bus.managed_objects(BlueZ.SERVICE, BlueZ.ROOT)
        return result.value if result.ok and isinstance(result.value, dict) else {}

    # -- adapter -----------------------------------------------------------------------------
    def adapter(self) -> Reading:
        """The first adapter. A machine without one shows the tile disabled, not "выключен"."""
        if not self._bus.has_service(BlueZ.SERVICE):
            return self._sysfs_adapter()
        for path, interfaces in sorted(self._tree().items()):
            values = interfaces.get(BlueZ.ADAPTER)
            if values is None:
                continue
            powered = bool(values.get("Powered", False))
            name = str(values.get("Alias") or values.get("Name") or path.rsplit("/", 1)[-1])
            return Reading.measured(1 if powered else 0, name, path, powered=powered,
                                    address=str(values.get("Address", "")),
                                    discovering=bool(values.get("Discovering", False)),
                                    discoverable=bool(values.get("Discoverable", False)))
        return Reading.missing(ADAPTER_ABSENT, BlueZ.SERVICE)

    def _sysfs_adapter(self) -> Reading:
        """Without bluetoothd all we can say is whether the kernel sees a radio.

        Presence is a fact; "powered" is not — rfkill state is a different file and BlueZ's own
        Powered is a different thing again — so the reading carries no value, only the name.
        """
        from pathlib import Path
        try:
            adapters = sorted(path.name for path in Path(self._sysfs_root).iterdir())
        except OSError:
            return Reading.missing(ADAPTER_ABSENT, self._sysfs_root)
        if not adapters:
            return Reading.missing(ADAPTER_ABSENT, self._sysfs_root)
        return Reading.measured(None, adapters[0], self._sysfs_root, powered=False,
                                address="", discovering=False, discoverable=False)

    def set_powered(self, powered: bool) -> Result:
        adapter = self.adapter()
        if not adapter.available:
            return Result.bad(adapter.detail, BlueZ.SERVICE)
        return self._bus.set(BlueZ.SERVICE, adapter.source, BlueZ.ADAPTER, "Powered",
                             Variant("b", bool(powered)))

    def start_discovery(self) -> Result:
        adapter = self.adapter()
        if not adapter.available:
            return Result.bad(adapter.detail, BlueZ.SERVICE)
        return self._bus.call(BlueZ.SERVICE, adapter.source, BlueZ.ADAPTER, "StartDiscovery")

    def stop_discovery(self) -> Result:
        adapter = self.adapter()
        if not adapter.available:
            return Result.bad(adapter.detail, BlueZ.SERVICE)
        return self._bus.call(BlueZ.SERVICE, adapter.source, BlueZ.ADAPTER, "StopDiscovery")

    # -- devices -----------------------------------------------------------------------------
    def devices(self, paired_only: bool = False) -> list[Reading]:
        """Known devices, connected first — the order the Windows quick-settings list uses.

        `value` is the battery percentage when the device publishes `org.bluez.Battery1`
        (headsets, mice, some keyboards) and None otherwise. That is the one number Windows shows
        next to a Bluetooth entry, and it is real or absent.
        """
        out: list[Reading] = []
        for path, interfaces in self._tree().items():
            values = interfaces.get(BlueZ.DEVICE)
            if values is None:
                continue
            paired = bool(values.get("Paired", False))
            if paired_only and not paired:
                continue
            battery = interfaces.get(BlueZ.BATTERY, {}).get("Percentage")
            name = str(values.get("Alias") or values.get("Name") or values.get("Address", ""))
            out.append(Reading.measured(
                int(battery) if battery is not None else None, name, path,
                address=str(values.get("Address", "")),
                connected=bool(values.get("Connected", False)),
                paired=paired, trusted=bool(values.get("Trusted", False)),
                icon=str(values.get("Icon", "")), rssi=values.get("RSSI")))
        return sorted(out, key=lambda item: (not item.get("connected"), not item.get("paired"),
                                             item.detail.casefold()))

    def connect(self, device_path: str) -> Result:
        return self._bus.call(BlueZ.SERVICE, device_path, BlueZ.DEVICE, "Connect", timeout=20.0)

    def disconnect(self, device_path: str) -> Result:
        return self._bus.call(BlueZ.SERVICE, device_path, BlueZ.DEVICE, "Disconnect", timeout=20.0)

    def pair(self, device_path: str) -> Result:
        """Pair, then trust. BlueZ needs an agent for a device that asks for a PIN; without one
        it returns an error, which is passed through — a silent failure would leave the user
        looking at a device that never connects.
        """
        paired = self._bus.call(BlueZ.SERVICE, device_path, BlueZ.DEVICE, "Pair", timeout=60.0)
        if not paired.ok:
            return paired
        self.trust(device_path)
        return paired

    def trust(self, device_path: str, trusted: bool = True) -> Result:
        return self._bus.set(BlueZ.SERVICE, device_path, BlueZ.DEVICE, "Trusted",
                             Variant("b", trusted))

    def remove(self, device_path: str) -> Result:
        """«Удалить устройство» — the adapter owns the pairing, so the adapter is asked."""
        adapter = self.adapter()
        if not adapter.available or not adapter.source.startswith("/org/bluez"):
            return Result.bad("адаптер Bluetooth не найден", BlueZ.SERVICE)
        return self._bus.call(BlueZ.SERVICE, adapter.source, BlueZ.ADAPTER, "RemoveDevice", "o",
                              [device_path], timeout=20.0)

    # -- change notification -----------------------------------------------------------------
    def watch(self, callback: Callable[[], None]) -> list:
        subscriptions = []
        properties = self._bus.on_properties_changed(lambda *_args: callback(),
                                                     path_namespace=BlueZ.NAMESPACE)
        if properties:
            subscriptions.append(properties)
        subscriptions.extend(self._bus.on_objects_changed(
            added=lambda *_args: callback(), removed=lambda *_args: callback(),
            sender=BlueZ.SERVICE))
        return subscriptions
