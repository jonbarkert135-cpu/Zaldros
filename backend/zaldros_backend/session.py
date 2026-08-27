"""The session: who is logged in, on what, and the keyboard layout.

The layout lives here rather than in a "keyboard" facet because on Wayland it is a property of the
session's compositor: KWin owns the keyboard, and `localectl` only ever reports what the image was
configured with, not what the user switched to.
"""

from __future__ import annotations

import os
from typing import Callable

from .bus import Bus, Result
from .catalog import KWinKeyboard, Login1
from .reading import NO_DATA, Reading

# Windows shows the layout as a three-letter badge in the UI language. A layout we have no name
# for keeps its own code rather than getting an invented translation.
LAYOUT_BADGES = {"ru": "РУС", "us": "ENG", "en": "ENG", "gb": "ENG", "ua": "УКР", "uk": "УКР",
                 "de": "DEU", "fr": "FRA", "es": "ESP", "it": "ITA", "pl": "POL", "he": "ИВР",
                 "tr": "TUR", "pt": "POR", "cz": "ČES", "kk": "ҚАЗ"}


def layout_badge(code: str) -> str:
    first = code.split(",")[0].strip().lower()
    return LAYOUT_BADGES.get(first, first.upper()[:3])


class SessionFacet:
    def __init__(self, system_bus: Bus, session_bus: Bus) -> None:
        self._system = system_bus
        self._session = session_bus

    # -- who and where -----------------------------------------------------------------------
    def user_name(self) -> str:
        return os.environ.get("USER") or os.environ.get("LOGNAME") or "пользователь"

    def session(self) -> Reading:
        """This login session, as logind sees it: seat, type, whether it is the active one."""
        values = self._system.get_all(Login1.SERVICE, Login1.SELF_SESSION, Login1.SESSION)
        if not values.ok:
            return Reading.missing(NO_DATA, Login1.SELF_SESSION)
        data = values.value
        seat = data.get("Seat")
        seat_name = str(seat[0]) if isinstance(seat, (tuple, list)) and seat else ""
        return Reading.measured(None, str(data.get("Type", "")), Login1.SELF_SESSION,
                                id=str(data.get("Id", "")), seat=seat_name,
                                active=bool(data.get("Active", False)),
                                locked_hint=bool(data.get("LockedHint", False)),
                                remote=bool(data.get("Remote", False)),
                                desktop=str(data.get("Desktop", "")))

    def lock(self) -> Result:
        return self._system.call(Login1.SERVICE, Login1.SELF_SESSION, Login1.SESSION, "Lock")

    def terminate(self) -> Result:
        """Log out. logind ends the session; the shell does not try to kill anything itself."""
        return self._system.call(Login1.SERVICE, Login1.SELF_SESSION, Login1.SESSION, "Terminate")

    def watch_lock(self, on_lock: Callable[[], None], on_unlock: Callable[[], None]) -> list:
        subscriptions = []
        for member, handler in (("Lock", on_lock), ("Unlock", on_unlock)):
            subscription = self._system.on_signal(lambda _message, cb=handler: cb(),
                                                  interface=Login1.SESSION, member=member,
                                                  path=Login1.SELF_SESSION)
            if subscription:
                subscriptions.append(subscription)
        return subscriptions

    # -- keyboard layout ---------------------------------------------------------------------
    def layouts(self) -> tuple[list[tuple[str, str, str]], int | None]:
        listed = self._session.call_one(KWinKeyboard.SERVICE, KWinKeyboard.PATH,
                                        KWinKeyboard.IFACE, "getLayoutsList")
        if not listed.ok or not listed.value:
            return ([], None)
        layouts = [(str(a), str(b), str(c)) for a, b, c in listed.value]
        current = self._session.call_one(KWinKeyboard.SERVICE, KWinKeyboard.PATH,
                                         KWinKeyboard.IFACE, "getLayout")
        index = int(current.value) if current.ok and current.value is not None else None
        return (layouts, index)

    def keyboard_layout(self) -> Reading:
        """The tray badge. Empty when nothing reports a layout — no badge beats a wrong badge."""
        layouts, index = self.layouts()
        if layouts and index is not None and index < len(layouts):
            return Reading.measured(index, layout_badge(layouts[index][0]), KWinKeyboard.SERVICE,
                                    name=layouts[index][1], code=layouts[index][0],
                                    count=len(layouts))
        language = os.environ.get("LANG", "").split(".")[0].split("_")[0]
        if len(language) == 2 and language.isalpha():
            return Reading.measured(None, layout_badge(language), "LANG", count=1)
        return Reading.missing("раскладка не определена", KWinKeyboard.SERVICE)

    def switch_layout(self) -> bool:
        """Next layout, the way clicking the Windows tray badge does."""
        layouts, index = self.layouts()
        if not layouts or index is None:
            return False
        result = self._session.call_one(KWinKeyboard.SERVICE, KWinKeyboard.PATH,
                                        KWinKeyboard.IFACE, "setLayout", "u",
                                        [(index + 1) % len(layouts)])
        return bool(result.ok and result.value)

    def watch_layout(self, callback: Callable[[], None]) -> list:
        subscription = self._session.on_signal(lambda _message: callback(),
                                               interface=KWinKeyboard.IFACE,
                                               member="layoutChanged")
        return [subscription] if subscription else []
