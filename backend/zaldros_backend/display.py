"""Displays: brightness and outputs.

Brightness has three possible owners and we try them in the order that keeps the session
consistent:

1. `org.kde.ScreenBrightness` — Plasma 6.5's per-display interface. Correct on a multi-monitor
   machine, where one number is the wrong shape.
2. `org.kde.Solid.PowerManagement.Actions.BrightnessControl` — PowerDevil's older single-value
   interface, still present. Note its scale is normalised (max is 10000, not the raw sysfs
   maximum), so it must be converted, not passed through [KDE Discuss + powerdevil sources,
   2026-08-27].
3. `/sys/class/backlight` — **read only**. Writing there needs root or a udev rule and races
   PowerDevil's own state; a slider that fights the daemon is worse than a slider that is
   disabled and says why.

Outputs (resolution, scale, refresh) are *not* on D-Bus at all on a KWin/Wayland session: they are
the `kde-output-management-v2` Wayland protocol, spoken by libkscreen. The shell is a Wayland
client, so the honest bridge is `kscreen-doctor -j`, and it is marked as such.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Callable

from .bus import Bus, Result
from .catalog import PowerDevil, ScreenBrightness
from .reading import NOT_SUPPORTED, Reading
from .wire import Variant

SYSFS_BACKLIGHT = "/sys/class/backlight"
KSCREEN_DOCTOR = "kscreen-doctor"
NO_CONTROL = "регулировка недоступна"


class DisplayFacet:
    def __init__(self, bus: Bus, sys_root: str = SYSFS_BACKLIGHT, runner=subprocess.run) -> None:
        self._bus = bus
        self._sys_root = sys_root
        self._run = runner

    # -- brightness --------------------------------------------------------------------------
    def brightness(self) -> Reading:
        modern = self._modern_brightness()
        if modern.available:
            return modern
        legacy = self._legacy_brightness()
        if legacy.available:
            return legacy
        return self._sysfs_brightness()

    def _displays(self) -> list[str]:
        names = self._bus.get(ScreenBrightness.SERVICE, ScreenBrightness.PATH,
                              ScreenBrightness.IFACE, "DisplaysDBusNames")
        if not names.ok or not isinstance(names.value, list):
            return []
        return [f"{ScreenBrightness.PATH}/{name}" for name in names.value]

    def _modern_brightness(self) -> Reading:
        if not self._bus.has_service(ScreenBrightness.SERVICE):
            return Reading.missing(NO_CONTROL, ScreenBrightness.SERVICE)
        for path in self._displays():
            values = self._bus.get_all(ScreenBrightness.SERVICE, path, ScreenBrightness.DISPLAY)
            if not values.ok:
                continue
            current = values.value.get("Brightness")
            maximum = values.value.get("MaxBrightness")
            if current is None or not maximum:
                continue
            return Reading.measured(round(int(current) / int(maximum) * 100), "", path,
                                    raw=int(current), raw_max=int(maximum),
                                    writable=True, api="org.kde.ScreenBrightness")
        return Reading.missing(NO_CONTROL, ScreenBrightness.SERVICE)

    def _legacy_brightness(self) -> Reading:
        if not self._bus.has_service(PowerDevil.SERVICE):
            return Reading.missing(NO_CONTROL, PowerDevil.SERVICE)
        current = self._bus.call_one(PowerDevil.SERVICE, PowerDevil.BRIGHTNESS_PATH,
                                     PowerDevil.BRIGHTNESS_IFACE, "brightness")
        maximum = self._bus.call_one(PowerDevil.SERVICE, PowerDevil.BRIGHTNESS_PATH,
                                     PowerDevil.BRIGHTNESS_IFACE, "brightnessMax")
        if not current.ok or not maximum.ok or not maximum.value:
            return Reading.missing(NO_CONTROL, PowerDevil.SERVICE)
        return Reading.measured(round(int(current.value) / int(maximum.value) * 100), "",
                                PowerDevil.BRIGHTNESS_PATH, raw=int(current.value),
                                raw_max=int(maximum.value), writable=True, api="powerdevil")

    def _sysfs_brightness(self) -> Reading:
        try:
            devices = sorted(Path(self._sys_root).iterdir())
        except OSError:
            return Reading.missing(NO_CONTROL, self._sys_root)
        for device in devices:
            current = _read_int(device / "brightness")
            maximum = _read_int(device / "max_brightness")
            if current is None or not maximum:
                continue
            # Readable, not writable: say so, so the UI can show the value and disable the slider
            # instead of offering a control that silently does nothing.
            return Reading.measured(round(current / maximum * 100), "", str(device),
                                    raw=current, raw_max=maximum, writable=False, api="sysfs")
        return Reading.missing(NO_CONTROL, self._sys_root)

    def set_brightness(self, percent: int) -> Result:
        value = max(0, min(100, int(percent)))
        current = self.brightness()
        if not current.available or not current.get("writable"):
            return Result.bad(current.detail or NOT_SUPPORTED, current.source)
        raw = round(value / 100 * current.get("raw_max", 100))
        if current.get("api") == "org.kde.ScreenBrightness":
            # SetBrightness(i value, u flags); flags 0 = show the on-screen indicator, as a
            # user-dragged slider should.
            return self._bus.call(ScreenBrightness.SERVICE, current.source,
                                  ScreenBrightness.DISPLAY, "SetBrightness", "iu", [raw, 0])
        return self._bus.call(PowerDevil.SERVICE, PowerDevil.BRIGHTNESS_PATH,
                              PowerDevil.BRIGHTNESS_IFACE, "setBrightness", "i", [raw])

    # -- outputs -----------------------------------------------------------------------------
    def outputs(self) -> list[Reading]:
        """Connected screens with their mode and scale, for the Settings display page.

        `kscreen-doctor -j` is libkscreen's own dump; it is the same data Plasma's display page
        uses, and asking it costs one process instead of reimplementing a Wayland protocol.
        """
        if not shutil.which(KSCREEN_DOCTOR):
            return []
        try:
            done = self._run([KSCREEN_DOCTOR, "-j"], capture_output=True, text=True, timeout=5.0)
        except (OSError, subprocess.SubprocessError):
            return []
        if done.returncode != 0:
            return []
        try:
            data = json.loads(done.stdout)
        except json.JSONDecodeError:
            return []
        return [reading for reading in (_output_reading(entry)
                                        for entry in data.get("outputs", [])) if reading]

    def set_output_mode(self, output: str, width: int, height: int,
                        refresh: float | None = None) -> Result:
        target = f"{int(width)}x{int(height)}" + (f"@{refresh:g}" if refresh else "")
        return self._kscreen(f"output.{output}.mode.{target}")

    def set_output_scale(self, output: str, scale: float) -> Result:
        return self._kscreen(f"output.{output}.scale.{scale:g}")

    def set_output_enabled(self, output: str, enabled: bool) -> Result:
        return self._kscreen(f"output.{output}.{'enable' if enabled else 'disable'}")

    def _kscreen(self, argument: str) -> Result:
        if not shutil.which(KSCREEN_DOCTOR):
            return Result.bad(f"{KSCREEN_DOCTOR} is not installed", KSCREEN_DOCTOR)
        try:
            done = self._run([KSCREEN_DOCTOR, argument], capture_output=True, text=True,
                             timeout=10.0)
        except (OSError, subprocess.SubprocessError) as exc:
            return Result.bad(str(exc), KSCREEN_DOCTOR)
        if done.returncode != 0:
            return Result.bad((done.stderr or done.stdout or "").strip(), KSCREEN_DOCTOR)
        return Result.good(True, KSCREEN_DOCTOR)

    # -- change notification -----------------------------------------------------------------
    def watch(self, callback: Callable[[], None]) -> list:
        subscriptions = []
        for service, path, interface in (
                (ScreenBrightness.SERVICE, None, ScreenBrightness.DISPLAY),
                (PowerDevil.SERVICE, PowerDevil.BRIGHTNESS_PATH, None)):
            subscription = self._bus.on_properties_changed(
                lambda *_args: callback(), sender=service, path=path, interface=interface)
            if subscription:
                subscriptions.append(subscription)
        legacy = self._bus.on_signal(lambda _message: callback(),
                                     interface=PowerDevil.BRIGHTNESS_IFACE,
                                     member="brightnessChanged")
        if legacy:
            subscriptions.append(legacy)
        return subscriptions


def _output_reading(entry: dict) -> Reading | None:
    name = str(entry.get("name") or "")
    if not name:
        return None
    modes = {str(mode.get("id")): mode for mode in entry.get("modes", [])}
    current = modes.get(str(entry.get("currentModeId")), {})
    size = current.get("size") or {}
    width, height = int(size.get("width", 0) or 0), int(size.get("height", 0) or 0)
    return Reading.measured(
        None, name, KSCREEN_DOCTOR, enabled=bool(entry.get("enabled", False)),
        connected=bool(entry.get("connected", False)),
        primary=bool(entry.get("primary", False)),
        width=width, height=height,
        refresh=round(float(current.get("refreshRate", 0) or 0), 2),
        scale=float(entry.get("scale", 1) or 1),
        rotation=int(entry.get("rotation", 1) or 1),
        modes=sorted({(int((mode.get("size") or {}).get("width", 0)),
                       int((mode.get("size") or {}).get("height", 0)))
                      for mode in entry.get("modes", [])}, reverse=True))


def _read_int(path: Path) -> int | None:
    try:
        return int(path.read_text().strip())
    except (OSError, ValueError):
        return None
