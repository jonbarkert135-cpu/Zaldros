"""Time, timezone and language — systemd-timedated and systemd-localed.

These two are the only writable owners of that state on a systemd machine, and both put every
setter behind polkit. Zaldros always calls them with `interactive=true`: a Settings page that a
user is looking at should raise the password prompt, not fail silently with "not authorized".

The keyboard layout is deliberately *not* here. On Wayland the running layout belongs to KWin
(see `session.py`); localed only holds the default the next session will start with. The Settings
page writes both, in that order, and says so.
"""

from __future__ import annotations

from typing import Callable

from .bus import Bus, Result
from .catalog import Locale1, TimeDate1
from .reading import NO_SERVICE, Reading

INTERACTIVE = True


class LocaleTimeFacet:
    def __init__(self, system_bus: Bus) -> None:
        self._bus = system_bus

    # -- time ----------------------------------------------------------------------------------
    def clock(self) -> Reading:
        """Timezone, NTP state and whether the RTC is on local time, in one read."""
        values = self._bus.get_all(TimeDate1.SERVICE, TimeDate1.PATH, TimeDate1.IFACE)
        if not values.ok or not isinstance(values.value, dict):
            return Reading.missing(NO_SERVICE, TimeDate1.SERVICE)
        data = values.value
        return Reading.measured(
            None, str(data.get("Timezone", "")), TimeDate1.PATH,
            timezone=str(data.get("Timezone", "")),
            ntp=bool(data.get("NTP", False)),
            can_ntp=bool(data.get("CanNTP", False)),
            synchronized=bool(data.get("NTPSynchronized", False)),
            local_rtc=bool(data.get("LocalRTC", False)),
            time_usec=int(data.get("TimeUSec", 0) or 0))

    def timezones(self) -> list[str]:
        """Every zone timedated will accept. Empty list when the service is absent — the UI then
        shows the current zone and no chooser, instead of a made-up list."""
        result = self._bus.call_one(TimeDate1.SERVICE, TimeDate1.PATH, TimeDate1.IFACE,
                                    "ListTimezones", timeout=10.0)
        if not result.ok or not isinstance(result.value, list):
            return []
        return [str(zone) for zone in result.value]

    def set_timezone(self, zone: str) -> Result:
        return self._bus.call(TimeDate1.SERVICE, TimeDate1.PATH, TimeDate1.IFACE,
                              "SetTimezone", "sb", [str(zone), INTERACTIVE], timeout=30.0)

    def set_ntp(self, enabled: bool) -> Result:
        return self._bus.call(TimeDate1.SERVICE, TimeDate1.PATH, TimeDate1.IFACE,
                              "SetNTP", "bb", [bool(enabled), INTERACTIVE], timeout=30.0)

    def set_local_rtc(self, local: bool) -> Result:
        return self._bus.call(TimeDate1.SERVICE, TimeDate1.PATH, TimeDate1.IFACE,
                              "SetLocalRTC", "bbb", [bool(local), False, INTERACTIVE],
                              timeout=30.0)

    # -- language ------------------------------------------------------------------------------
    def locale(self) -> Reading:
        """The system locale, split into its variables. LANG is the one Settings shows."""
        values = self._bus.get_all(Locale1.SERVICE, Locale1.PATH, Locale1.IFACE)
        if not values.ok or not isinstance(values.value, dict):
            return Reading.missing(NO_SERVICE, Locale1.SERVICE)
        data = values.value
        variables: dict[str, str] = {}
        for item in data.get("Locale", []) or []:
            name, _, value = str(item).partition("=")
            if name:
                variables[name] = value
        lang = variables.get("LANG", "")
        return Reading.measured(
            None, lang, Locale1.PATH, lang=lang, variables=variables,
            x11_layout=str(data.get("X11Layout", "")),
            x11_variant=str(data.get("X11Variant", "")),
            x11_model=str(data.get("X11Model", "")),
            x11_options=str(data.get("X11Options", "")),
            vconsole=str(data.get("VConsoleKeymap", "")))

    def set_language(self, lang: str) -> Result:
        """Set LANG. Everything else in the locale is left as the image configured it — changing
        LC_* behind the user's back is how a desktop ends up with English dates and Russian menus.
        """
        return self._bus.call(Locale1.SERVICE, Locale1.PATH, Locale1.IFACE, "SetLocale", "asb",
                              [[f"LANG={lang}"], INTERACTIVE], timeout=30.0)

    def set_x11_keyboard(self, layout: str, variant: str = "", model: str = "",
                         options: str = "") -> Result:
        """The *default* keyboard layout for the next session. `convert=true` makes localed set
        the matching console keymap too, which is what keeps a TTY usable after the change."""
        return self._bus.call(Locale1.SERVICE, Locale1.PATH, Locale1.IFACE, "SetX11Keyboard",
                              "ssssbb", [layout, model, variant, options, True, INTERACTIVE],
                              timeout=30.0)

    def locales(self, runner=None) -> list[str]:
        """The locales this machine has generated, from `locale -a`.

        Not from /usr/share/i18n/SUPPORTED: that file lists what *could* be generated, and
        offering a language the system cannot actually switch to is the same as offering nothing.
        UTF-8 forms only, because that is what LANG should ever be set to now.
        """
        import subprocess
        run = runner if runner is not None else subprocess.run
        try:
            done = run(["locale", "-a"], capture_output=True, text=True, timeout=5.0)
        except (OSError, subprocess.SubprocessError):
            return []
        if done.returncode != 0:
            return []
        names = {line.strip() for line in done.stdout.splitlines()
                 if line.strip().lower().endswith(("utf-8", "utf8"))}
        return sorted(name.replace("utf8", "UTF-8") for name in names)

    # -- change notification ---------------------------------------------------------------------
    def watch(self, callback: Callable[[], None]) -> list:
        subscriptions = []
        for service, path in ((TimeDate1.SERVICE, TimeDate1.PATH),
                              (Locale1.SERVICE, Locale1.PATH)):
            subscription = self._bus.on_properties_changed(lambda *_args: callback(),
                                                           sender=service, path=path)
            if subscription:
                subscriptions.append(subscription)
        return subscriptions
