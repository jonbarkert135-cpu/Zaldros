"""The honesty contract, shared by every facet.

spec PART 3 §25: Zaldros never invents system information. A value that cannot be measured on
this machine comes back unavailable, with the reason in the user's language, and the UI shows
that reason instead of a plausible-looking number.

`source` is the last link in the chain: the D-Bus name, the tool, or the sysfs path the value came
from. It is what turns "the battery says 87 %" into a claim someone can check.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# The wordings the whole shell uses for "there is nothing to show". One list, so two panels never
# phrase the same absence differently.
NO_DATA = "нет данных"
NO_SERVICE = "служба недоступна"
NOT_PRESENT = "устройство не найдено"
NOT_SUPPORTED = "не поддерживается"


@dataclass(frozen=True)
class Reading:
    """One value, plus whether it is real and where it came from."""

    available: bool
    value: int | None = None
    detail: str = ""
    source: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def measured(cls, value: int | None, detail: str = "", source: str = "",
                 **extra: Any) -> "Reading":
        return cls(True, value, detail, source, extra)

    @classmethod
    def missing(cls, detail: str = NO_DATA, source: str = "") -> "Reading":
        return cls(False, None, detail, source, {})

    def get(self, key: str, default: Any = None) -> Any:
        return self.extra.get(key, default)

    @property
    def percent(self) -> int:
        """The value as the UI wants it: -1 when there is none, so QML can test `>= 0`."""
        return -1 if not self.available or self.value is None else int(self.value)
