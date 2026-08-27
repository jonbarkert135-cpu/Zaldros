"""Power: batteries and AC from UPower, sleep and shutdown from logind.

Two services, one Zaldros concept. The tray asks `battery()`; whether that number comes from a
laptop battery, a UPS or nothing at all is this file's problem, not the UI's.
"""

from __future__ import annotations

from typing import Any, Callable

from .bus import Bus, Result
from .catalog import Login1, UPower
from .reading import NO_DATA, NO_SERVICE, NOT_PRESENT, Reading

# The wording the shell already renders in quick settings. Kept verbatim: the
# backend replaced where a reading comes from, not a single pixel of what is shown.
BATTERY_ABSENT = "батарея не обнаружена"

# What the Windows tray calls the state, in the interface's own language.
STATE_TEXT = {
    "charging": "зарядка", "discharging": "разряжается", "empty": "разряжена",
    "fully-charged": "заряжена", "pending-charge": "ожидает зарядки",
    "pending-discharge": "ожидает разрядки", "unknown": "состояние неизвестно",
}


class PowerFacet:
    """UPower + logind behind one object."""

    def __init__(self, bus: Bus, sysfs_root: str = "/sys/class/power_supply") -> None:
        self._bus = bus
        self._sysfs_root = sysfs_root

    # -- battery -----------------------------------------------------------------------------
    def battery(self) -> Reading:
        """The battery the tray shows.

        UPower composes a `DisplayDevice` out of every battery in the machine — that is what
        GNOME's and Plasma's indicators read, and it is the right answer for a two-battery
        ThinkPad. When the composite says there is no battery, we do not fall back to guessing.
        """
        if not self._bus.has_service(UPower.SERVICE):
            return self._sysfs_battery()
        properties = self._bus.get_all(UPower.SERVICE, UPower.DISPLAY_DEVICE, UPower.DEVICE_IFACE)
        if not properties.ok:
            return self._sysfs_battery()
        reading = self._battery_from(properties.value, UPower.DISPLAY_DEVICE)
        return reading if reading.available else self._sysfs_battery()

    def _sysfs_battery(self) -> Reading:
        """/sys/class/power_supply, for a machine with no UPower on it.

        The shell read this directly before the backend existed, and a live installer or a rescue
        session may well have no UPower running. Keeping the fallback means the layer added
        nothing that could take a reading away — only the source line changes.
        """
        from pathlib import Path
        root = Path(self._sysfs_root)
        try:
            candidates = sorted(path for path in root.iterdir() if path.name.startswith("BAT"))
        except OSError:
            return Reading.missing(NO_DATA, str(root))
        for path in candidates:
            try:
                percent = int((path / "capacity").read_text().strip())
            except (OSError, ValueError):
                continue
            try:
                status = (path / "status").read_text().strip()
            except OSError:
                status = ""
            state = {"Charging": "charging", "Discharging": "discharging",
                     "Full": "fully-charged", "Not charging": "pending-charge"}.get(status,
                                                                                    "unknown")
            return Reading.measured(percent, STATE_TEXT.get(state, status or "состояние неизвестно"),
                                    str(path), state=state,
                                    charging=state in ("charging", "fully-charged"),
                                    seconds_left=0, time_text="")
        return Reading.missing(BATTERY_ABSENT, str(root))

    def _battery_from(self, values: dict[str, Any], path: str) -> Reading:
        kind = UPower.TYPE.get(int(values.get("Type", 0) or 0), "unknown")
        present = bool(values.get("IsPresent", False))
        if kind not in ("battery", "ups") or not present:
            return Reading.missing(NOT_PRESENT, path)
        percentage = values.get("Percentage")
        if percentage is None:
            return Reading.missing(NOT_PRESENT, path)
        state = UPower.STATE.get(int(values.get("State", 0) or 0), "unknown")
        seconds = int(values.get("TimeToEmpty", 0) or 0) or int(values.get("TimeToFull", 0) or 0)
        return Reading.measured(
            round(float(percentage)), STATE_TEXT.get(state, state), path,
            state=state,
            charging=state in ("charging", "fully-charged", "pending-charge"),
            seconds_left=seconds,
            time_text=_duration(seconds),
            energy_rate=float(values.get("EnergyRate", 0.0) or 0.0),
            warning=UPower.WARNING.get(int(values.get("WarningLevel", 0) or 0), "unknown"),
            icon=str(values.get("IconName", "")),
        )

    def devices(self) -> list[Reading]:
        """Every powered thing UPower knows: batteries, mice, headsets, the UPS.

        Windows 11 lists connected devices with their charge in quick settings; this is where
        those numbers come from, and each one keeps the object path it was read off.
        """
        listed = self._bus.call_one(UPower.SERVICE, UPower.PATH, UPower.IFACE, "EnumerateDevices")
        if not listed.ok:
            return []
        out: list[Reading] = []
        for path in listed.value or []:
            properties = self._bus.get_all(UPower.SERVICE, path, UPower.DEVICE_IFACE)
            if not properties.ok:
                continue
            values = properties.value
            percentage = values.get("Percentage")
            kind = UPower.TYPE.get(int(values.get("Type", 0) or 0), "unknown")
            if percentage is None or not values.get("IsPresent", True):
                continue
            model = str(values.get("Model") or values.get("NativePath") or kind)
            out.append(Reading.measured(round(float(percentage)), model, path, kind=kind,
                                        vendor=str(values.get("Vendor", "")),
                                        state=UPower.STATE.get(int(values.get("State", 0) or 0),
                                                               "unknown")))
        return out

    def on_battery(self) -> Reading:
        """True when the machine is running off the battery — the taskbar's plug glyph."""
        value = self._bus.get(UPower.SERVICE, UPower.PATH, UPower.IFACE, "OnBattery")
        if not value.ok:
            return Reading.missing(NO_SERVICE, value.source)
        return Reading.measured(1 if value.value else 0,
                                "от батареи" if value.value else "от сети", value.source,
                                on_battery=bool(value.value))

    def lid_closed(self) -> Reading:
        present = self._bus.get(UPower.SERVICE, UPower.PATH, UPower.IFACE, "LidIsPresent")
        if not present.ok or not present.value:
            return Reading.missing(NOT_PRESENT, UPower.SERVICE)
        closed = self._bus.get(UPower.SERVICE, UPower.PATH, UPower.IFACE, "LidIsClosed")
        if not closed.ok:
            return Reading.missing(NO_SERVICE, closed.source)
        return Reading.measured(1 if closed.value else 0,
                                "крышка закрыта" if closed.value else "крышка открыта",
                                closed.source)

    # -- what the power button may offer -----------------------------------------------------
    def capabilities(self) -> dict[str, bool]:
        """Which entries the Start menu's power button is allowed to draw.

        logind answers "yes" / "no" / "na" / "challenge"; "challenge" means polkit will ask the
        user, which is still an offer we may make. Anything else is not drawn — Windows greys out
        what the machine cannot do, it does not fail after the click.
        """
        out: dict[str, bool] = {}
        for action, method in (("poweroff", "CanPowerOff"), ("reboot", "CanReboot"),
                               ("suspend", "CanSuspend"), ("hibernate", "CanHibernate"),
                               ("hybrid-sleep", "CanHybridSleep")):
            reply = self._bus.call_one(Login1.SERVICE, Login1.PATH, Login1.MANAGER, method)
            out[action] = bool(reply.ok and reply.value in Login1.CAN_YES)
        return out

    def _act(self, method: str) -> Result:
        return self._bus.call(Login1.SERVICE, Login1.PATH, Login1.MANAGER, method, "b", [True])

    def suspend(self) -> Result:
        return self._act("Suspend")

    def hibernate(self) -> Result:
        return self._act("Hibernate")

    def power_off(self) -> Result:
        return self._act("PowerOff")

    def reboot(self) -> Result:
        return self._act("Reboot")

    def lock_session(self) -> Result:
        return self._bus.call(Login1.SERVICE, Login1.PATH, Login1.MANAGER, "LockSessions")

    # -- change notification -----------------------------------------------------------------
    def watch(self, callback: Callable[[], None]) -> list:
        """Wake on power changes instead of asking every second.

        Three subscriptions cover everything a tray shows: the composite battery's properties,
        the manager's own (OnBattery, LidIsClosed), and logind's sleep transitions — the last one
        matters because after a resume every reading is stale at once.
        """
        subscriptions = []
        for path_namespace, interface in ((UPower.PATH, UPower.IFACE),
                                          (UPower.DEVICE_NAMESPACE, UPower.DEVICE_IFACE)):
            subscription = self._bus.on_properties_changed(
                lambda *_args: callback(), sender=None, path_namespace=path_namespace,
                interface=interface)
            if subscription:
                subscriptions.append(subscription)
        sleep = self._bus.on_signal(lambda _message: callback(), interface=Login1.MANAGER,
                                    member="PrepareForSleep")
        if sleep:
            subscriptions.append(sleep)
        return subscriptions


def _duration(seconds: int) -> str:
    """"2 ч 15 мин" — the way Windows writes the remaining time, in Russian."""
    if seconds <= 0:
        return ""
    hours, minutes = divmod(seconds // 60, 60)
    if hours and minutes:
        return f"{hours} ч {minutes} мин"
    if hours:
        return f"{hours} ч"
    return f"{minutes} мин"
