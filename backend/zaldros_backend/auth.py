"""Privilege: polkit.

Zaldros never runs the shell as root and never calls `pkexec` behind the user's back. When a panel
offers an action that needs privilege, it asks polkit first, so the button can be drawn the way
Windows draws it — with the shield, or greyed out — instead of failing after the click.

Reference: polkit reference manual, `org.freedesktop.PolicyKit1.Authority`
(https://polkit.pages.freedesktop.org/polkit/), fetched 2026-08-27.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from .bus import Bus
from .catalog import Polkit
from .wire import Variant

# The actions the shell actually offers. Naming them here keeps a typo from silently becoming
# "not authorised" — an unknown action id is an error from polkit, and we surface it.
ACTIONS = {
    "mount": "org.freedesktop.udisks2.filesystem-mount",
    "mount-system": "org.freedesktop.udisks2.filesystem-mount-system",
    "manage-services": "org.freedesktop.systemd1.manage-units",
    "network-settings": "org.freedesktop.NetworkManager.settings.modify.system",
    "network-control": "org.freedesktop.NetworkManager.network-control",
    "power-off-multiple": "org.freedesktop.login1.power-off-multiple-sessions",
    "set-time": "org.freedesktop.timedate1.set-time",
    "set-hostname": "org.freedesktop.hostname1.set-static-hostname",
}


@dataclass(frozen=True)
class Authorization:
    """polkit's verdict. `challenge` means "yes, after the user types a password"."""

    allowed: bool
    challenge: bool
    reason: str = ""

    @property
    def offerable(self) -> bool:
        """Whether the UI may draw the control at all — with a shield when it is a challenge."""
        return self.allowed or self.challenge


class AuthFacet:
    def __init__(self, bus: Bus) -> None:
        self._bus = bus

    @property
    def available(self) -> bool:
        return self._bus.has_service(Polkit.SERVICE)

    def check(self, action: str, interactive: bool = False) -> Authorization:
        """Ask polkit about one action for this process.

        The subject is `unix-process` with our own pid and start time, which is what a session
        application is expected to send. `interactive=False` by default: a check that pops an
        authentication dialog just because a panel opened is exactly the behaviour Windows users
        complain about on Linux.
        """
        action_id = ACTIONS.get(action, action)
        if not self.available:
            return Authorization(False, False, "polkit is not running")
        subject = ("unix-process", {"pid": Variant("u", os.getpid()),
                                    "start-time": Variant("t", _start_time())})
        flags = Polkit.ALLOW_USER_INTERACTION if interactive else 0
        result = self._bus.call_one(
            Polkit.SERVICE, Polkit.PATH, Polkit.AUTHORITY, "CheckAuthorization",
            "(sa{sv})sa{ss}us", [subject, action_id, {}, flags, ""],
            timeout=60.0 if interactive else 5.0)
        if not result.ok:
            return Authorization(False, False, result.error)
        value = result.value
        if not isinstance(value, (tuple, list)) or len(value) < 2:
            return Authorization(False, False, "polkit answered in a shape we do not understand")
        return Authorization(bool(value[0]), bool(value[1]))


def _start_time() -> int:
    """Field 22 of /proc/self/stat, in clock ticks. polkit uses it to pin the identity of a pid.

    Without it a recycled pid could inherit somebody else's authorisation, which is the whole
    reason the field is in the subject.
    """
    try:
        with open("/proc/self/stat", encoding="utf-8") as handle:
            raw = handle.read()
    except OSError:
        return 0
    # The second field is the executable name in parentheses and may itself contain spaces.
    tail = raw.rpartition(")")[2].split()
    try:
        return int(tail[19])
    except (IndexError, ValueError):
        return 0
