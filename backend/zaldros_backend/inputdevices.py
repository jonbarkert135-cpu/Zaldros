"""Mice, touchpads and keyboards, as the running compositor sees them.

KWin publishes every libinput device on the session bus: `/org/kde/KWin/InputDevice` lists the
sys names, and each `/org/kde/KWin/InputDevice/<sysName>` carries the device's settings as
writable properties [KDE/kwin src/backends/libinput/{connection,device}.{cpp,h}, 2026-08-28].

Two consequences shape this facet:

* **Writes take effect immediately and are not persisted by us.** KWin applies the property to
  libinput at once and stores it in `kcminputrc`; nothing here has to restart or reload anything.
* **Every option has a `supports*` companion.** A touchpad without tap-to-click has the property
  but changing it does nothing, so the facet reports what the hardware supports and Settings can
  grey the row out instead of offering a switch that lies.
"""

from __future__ import annotations

from typing import Any, Callable

from .bus import Bus, Result
from .catalog import KWinInput
from .reading import NOT_PRESENT, NOT_SUPPORTED, Reading
from .wire import Variant

# name -> (D-Bus property, its `supports*` flag or "" when the device always has it, signature)
OPTIONS: dict[str, tuple[str, str, str]] = {
    "enabled": ("enabled", "supportsDisableEvents", "b"),
    "left_handed": ("leftHanded", "supportsLeftHanded", "b"),
    "natural_scroll": ("naturalScroll", "supportsNaturalScroll", "b"),
    "tap_to_click": ("tapToClick", "", "b"),
    "tap_and_drag": ("tapAndDrag", "", "b"),
    "disable_while_typing": ("disableWhileTyping", "supportsDisableWhileTyping", "b"),
    "middle_emulation": ("middleEmulation", "supportsMiddleEmulation", "b"),
    "acceleration": ("pointerAcceleration", "supportsPointerAcceleration", "d"),
    "scroll_factor": ("scrollFactor", "", "d"),
}


class InputFacet:
    def __init__(self, session_bus: Bus) -> None:
        self._bus = session_bus

    # -- inventory -------------------------------------------------------------------------------
    def sys_names(self) -> list[str]:
        names = self._bus.get(KWinInput.SERVICE, KWinInput.MANAGER_PATH, KWinInput.MANAGER,
                              "devicesSysNames")
        if not names.ok or not isinstance(names.value, list):
            return []
        return [str(name) for name in names.value]

    def devices(self, kind: str = "") -> list[Reading]:
        """Every input device, optionally only the pointers / touchpads / keyboards.

        `kind` is one of KWinInput.KINDS; anything else returns nothing rather than everything,
        so a typo cannot silently show the mouse page a keyboard.
        """
        if kind and kind not in KWinInput.KINDS:
            return []
        out: list[Reading] = []
        for sys_name in self.sys_names():
            reading = self.device(sys_name)
            if not reading.available:
                continue
            if kind and not reading.get(kind):
                continue
            out.append(reading)
        return out

    def device(self, sys_name: str) -> Reading:
        path = f"{KWinInput.MANAGER_PATH}/{sys_name}"
        values = self._bus.get_all(KWinInput.SERVICE, path, KWinInput.DEVICE)
        if not values.ok or not isinstance(values.value, dict) or not values.value:
            return Reading.missing(NOT_PRESENT, path)
        data = values.value
        extra: dict[str, Any] = {"sys_name": sys_name, "path": path}
        for kind in KWinInput.KINDS:
            extra[kind] = bool(data.get(kind, False))
        for name, (prop, supports, _signature) in OPTIONS.items():
            if prop in data:
                extra[name] = data[prop]
            extra[f"can_{name}"] = bool(data.get(supports, True)) if supports else prop in data
        return Reading.measured(None, str(data.get("name", sys_name)), path, **extra)

    # -- writing ---------------------------------------------------------------------------------
    def option(self, sys_name: str, option: str) -> Reading:
        """One setting of one device, with whether it can be changed at all."""
        if option not in OPTIONS:
            return Reading.missing(NOT_SUPPORTED, option)
        device = self.device(sys_name)
        if not device.available:
            return device
        if not device.get(f"can_{option}"):
            return Reading.missing(NOT_SUPPORTED, device.get("path", ""))
        # The extra is called `setting`, not `value`: `Reading.value` is the numeric slot and a
        # boolean libinput option is not a number.
        return Reading.measured(None, str(device.get(option)), device.get("path", ""),
                                setting=device.get(option), device=device.detail,
                                option=option)

    def set_option(self, sys_name: str, option: str, value: Any) -> Result:
        if option not in OPTIONS:
            return Result.bad(f"unknown input option {option!r}", KWinInput.DEVICE)
        prop, _supports, signature = OPTIONS[option]
        device = self.device(sys_name)
        if not device.available:
            return Result.bad("device is gone", device.source)
        if not device.get(f"can_{option}"):
            return Result.bad(f"{sys_name} does not support {option}", device.get("path", ""))
        typed = bool(value) if signature == "b" else float(value)
        return self._bus.set(KWinInput.SERVICE, device.get("path", ""), KWinInput.DEVICE, prop,
                             Variant(signature, typed))

    def set_for_kind(self, kind: str, option: str, value: Any) -> Result:
        """Apply one setting to every device of a kind — what a Settings switch means when a
        machine has two mice. Fails only if *no* device took it, and says how many did."""
        devices = self.devices(kind)
        if not devices:
            return Result.bad(f"no {kind} devices", KWinInput.MANAGER_PATH)
        applied, errors = 0, []
        for device in devices:
            result = self.set_option(device.get("sys_name", ""), option, value)
            if result.ok:
                applied += 1
            else:
                errors.append(result.error)
        if applied:
            return Result.good(applied, KWinInput.MANAGER_PATH)
        return Result.bad("; ".join(errors) or "no device accepted the change",
                          KWinInput.MANAGER_PATH)

    def value_for_kind(self, kind: str, option: str) -> Reading:
        """What the switch should show for a kind: the first device that has the option."""
        for device in self.devices(kind):
            reading = self.option(device.get("sys_name", ""), option)
            if reading.available:
                return reading
        return Reading.missing(NOT_PRESENT, KWinInput.MANAGER_PATH)

    # -- change notification -----------------------------------------------------------------
    def watch(self, callback: Callable[[], None]) -> list:
        subscription = self._bus.on_properties_changed(
            lambda *_args: callback(), path_namespace=KWinInput.MANAGER_PATH,
            interface=KWinInput.DEVICE)
        return [subscription] if subscription else []
