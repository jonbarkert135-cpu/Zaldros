"""The shell's seam to the Zaldros backend.

This file used to *be* the system layer: it read /sys/class/power_supply, ran `wpctl`, ran `gdbus`,
ran `localectl` and parsed each of their outputs. All of that now lives in `zaldros_backend`, where
it is one D-Bus layer instead of five one-off readers, it is event-driven, and it is tested against
mock UPower / NetworkManager / BlueZ / udisks2 services standing on a real bus.

What is left here is the seam and nothing else: one shared backend instance for the process, and
the handful of names the shell's models and Settings pages already import. `Reading` is
re-exported from the backend so the honesty contract has exactly one definition.
"""

from __future__ import annotations

from zaldros_backend import Reading, ZaldrosBackend
from zaldros_backend.session import LAYOUT_BADGES, layout_badge   # noqa: F401 - re-exported

__all__ = ["Reading", "LAYOUT_BADGES", "backend", "keyboard_layout", "layout_badge",
           "snapshot", "switch_layout", "user_name"]

_BACKEND: ZaldrosBackend | None = None


def backend() -> ZaldrosBackend:
    """The one backend this process talks to.

    A single instance on purpose: two would mean two D-Bus connections, two sets of match rules
    and two copies of every signal. The shell, its Settings pages and its flyouts all share this.
    """
    global _BACKEND
    if _BACKEND is None:
        _BACKEND = ZaldrosBackend()
    return _BACKEND


def set_backend(instance: ZaldrosBackend | None) -> None:
    """Point the shell at another backend — a test bus, or none at all."""
    global _BACKEND
    _BACKEND = instance


def snapshot() -> dict[str, Reading]:
    """Every tray and quick-settings reading, in one pass."""
    return backend().tray()


def user_name() -> str:
    return backend().session.user_name()


def keyboard_layout() -> Reading:
    return backend().session.keyboard_layout()


def switch_layout() -> bool:
    return backend().session.switch_layout()
