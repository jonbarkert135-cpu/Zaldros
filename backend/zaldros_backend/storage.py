"""Storage: udisks2 — the drives Explorer's «Этот компьютер» lists, and mounting them.

Explorer currently reads /proc/mounts, which shows what is mounted and nothing else: it cannot
see a USB stick that is plugged in but not mounted, and it cannot mount one. udisks2 can do both
without root, because mounting a removable volume is a polkit action a session user already holds.
"""

from __future__ import annotations

from typing import Any, Callable

from .bus import Bus, Result, decode_byte_string
from .catalog import UDisks2
from .reading import NO_SERVICE, Reading


class StorageFacet:
    def __init__(self, bus: Bus) -> None:
        self._bus = bus

    def _tree(self) -> dict[str, dict[str, dict[str, Any]]]:
        result = self._bus.managed_objects(UDisks2.SERVICE, UDisks2.PATH)
        return result.value if result.ok and isinstance(result.value, dict) else {}

    def volumes(self, include_system: bool = False) -> list[Reading]:
        """Every mountable filesystem, with its label, size and mount point.

        `value` is the fill percentage where it can be measured (a mounted filesystem), None
        otherwise — an unmounted volume has no used-space number and does not get invented one.
        Loop devices and udisks2's own "ignore" hint are skipped; system partitions only appear
        when asked for, because Windows does not put /boot/efi in «Этот компьютер» either.
        """
        if not self._bus.has_service(UDisks2.SERVICE):
            return []
        tree = self._tree()
        out: list[Reading] = []
        for path, interfaces in sorted(tree.items()):
            block = interfaces.get(UDisks2.BLOCK)
            filesystem = interfaces.get(UDisks2.FILESYSTEM)
            if block is None or filesystem is None:
                continue
            if block.get("HintIgnore") or not block.get("IdUsage") == "filesystem":
                continue
            device = decode_byte_string(block.get("Device"))
            if device.startswith("/dev/loop"):
                continue
            is_system = bool(block.get("HintSystem", False))
            if is_system and not include_system:
                continue
            mount_points = [decode_byte_string(entry)
                            for entry in (filesystem.get("MountPoints") or [])]
            drive_path = str(block.get("Drive") or "/")
            drive = tree.get(drive_path, {}).get(UDisks2.DRIVE, {})
            label = (str(block.get("IdLabel") or "")
                     or " ".join(part for part in (str(drive.get("Vendor", "")),
                                                   str(drive.get("Model", ""))) if part).strip()
                     or device)
            used_percent = _fill_percent(mount_points[0]) if mount_points else None
            out.append(Reading.measured(
                used_percent, label, path, device=device,
                mount_point=mount_points[0] if mount_points else "",
                mounted=bool(mount_points),
                size=int(block.get("Size", 0) or 0),
                filesystem=str(block.get("IdType") or ""),
                uuid=str(block.get("IdUUID") or ""),
                read_only=bool(block.get("ReadOnly", False)),
                system=is_system,
                removable=bool(drive.get("Removable", False)),
                ejectable=bool(drive.get("Ejectable", False)),
                connection=str(drive.get("ConnectionBus", "")),
                drive=drive_path))
        return out

    def drives(self) -> list[Reading]:
        out: list[Reading] = []
        for path, interfaces in sorted(self._tree().items()):
            drive = interfaces.get(UDisks2.DRIVE)
            if drive is None:
                continue
            name = " ".join(part for part in (str(drive.get("Vendor", "")),
                                              str(drive.get("Model", ""))) if part).strip()
            out.append(Reading.measured(None, name or path.rsplit("/", 1)[-1], path,
                                        size=int(drive.get("Size", 0) or 0),
                                        removable=bool(drive.get("Removable", False)),
                                        ejectable=bool(drive.get("Ejectable", False)),
                                        media_available=bool(drive.get("MediaAvailable", True)),
                                        connection=str(drive.get("ConnectionBus", "")),
                                        serial=str(drive.get("Serial", ""))))
        return out

    def mount(self, volume_path: str) -> Result:
        """Mount and return the mount point udisks2 chose, so Explorer can navigate there."""
        result = self._bus.call_one(UDisks2.SERVICE, volume_path, UDisks2.FILESYSTEM, "Mount",
                                    "a{sv}", [{}], timeout=30.0)
        return result

    def unmount(self, volume_path: str) -> Result:
        return self._bus.call(UDisks2.SERVICE, volume_path, UDisks2.FILESYSTEM, "Unmount",
                              "a{sv}", [{}], timeout=30.0)

    def eject(self, drive_path: str) -> Result:
        return self._bus.call(UDisks2.SERVICE, drive_path, UDisks2.DRIVE, "Eject", "a{sv}", [{}],
                              timeout=30.0)

    def watch(self, callback: Callable[[], None]) -> list:
        """A USB stick appearing is InterfacesAdded, not a change to a property we already read."""
        subscriptions = list(self._bus.on_objects_changed(
            added=lambda *_args: callback(), removed=lambda *_args: callback(),
            sender=UDisks2.SERVICE))
        properties = self._bus.on_properties_changed(lambda *_args: callback(),
                                                     path_namespace=UDisks2.NAMESPACE)
        if properties:
            subscriptions.append(properties)
        return subscriptions

    @property
    def available(self) -> bool:
        return self._bus.has_service(UDisks2.SERVICE)

    @property
    def unavailable_reason(self) -> str:
        return "" if self.available else NO_SERVICE


def _fill_percent(mount_point: str) -> int | None:
    import os
    try:
        stats = os.statvfs(mount_point)
    except OSError:
        return None
    total = stats.f_blocks * stats.f_frsize
    if total <= 0:
        return None
    free = stats.f_bavail * stats.f_frsize
    return round((total - free) / total * 100)
