# SPDX-License-Identifier: GPL-3.0-or-later
"""Sorting, searching and formatting for «Диспетчер задач» — no Qt, so it stays testable.

The measuring lives in `zaldros_backend.processes`; this module is the part that decides what a
Windows user sees: which column sorts which way by default, how a byte count becomes «184 МБ»,
and what a column shows when the value is unknown (a dash — never a zero).
"""

from __future__ import annotations

from dataclasses import dataclass

# Windows Task Manager's columns, in its order. `numeric` decides the default direction: names
# sort A→Я ascending, resource columns sort heaviest-first, which is what the user came for.
COLUMNS = (("name", "Имя", False), ("cpu", "ЦП", True), ("rss", "Память", True),
           ("readBytes", "Диск", True), ("threads", "Потоки", True), ("pid", "ИД", True),
           ("user", "Пользователь", False), ("stateText", "Состояние", False))
COLUMN_KEYS = tuple(key for key, _, _ in COLUMNS)
NUMERIC = {key for key, _, numeric in COLUMNS if numeric}

DASH = "—"


def format_bytes(value: int | None) -> str:
    """Windows uses МБ for process memory and ГБ only in the summary; so do we."""
    if value is None:
        return DASH
    if value < 1024:
        return f"{value} Б"
    for unit, size in (("КБ", 1024), ("МБ", 1024 ** 2), ("ГБ", 1024 ** 3), ("ТБ", 1024 ** 4)):
        if value < size * 1024:
            scaled = value / size
            return f"{scaled:.1f} {unit}".replace(".", ",") if scaled < 10 else \
                f"{round(scaled)} {unit}"
    return f"{value / 1024 ** 4:.1f} ТБ"


def format_rate(value: float | None) -> str:
    if value is None:
        return DASH
    return f"{format_bytes(int(value))}/с"


def format_percent(value: float | None) -> str:
    if value is None:
        return DASH
    return f"{value:.1f} %".replace(".", ",")


def format_uptime(seconds: int) -> str:
    """The «Время работы» field, in Windows's d:hh:mm:ss shape."""
    days, rest = divmod(max(seconds, 0), 86400)
    hours, rest = divmod(rest, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{days}:{hours:02d}:{minutes:02d}:{secs:02d}"


def matches(row: dict, query: str) -> bool:
    """Search over the three fields a user actually types: name, command line, PID."""
    text = query.strip().lower()
    if not text:
        return True
    return (text in str(row.get("name", "")).lower()
            or text in str(row.get("cmdline", "")).lower()
            or text == str(row.get("pid", "")))


def sort_rows(rows: list[dict], key: str, descending: bool | None = None) -> list[dict]:
    """Stable sort with unknowns last, whichever direction is chosen.

    A process whose CPU share is not known yet (first sample) must not be sorted as if it were
    0 %: it is placed after every known value in both directions, so the unknown never displaces
    a real reading from the top of the list.
    """
    if key not in COLUMN_KEYS:
        raise ValueError(f"unknown column {key!r}; known: {', '.join(COLUMN_KEYS)}")
    reverse = (key in NUMERIC) if descending is None else bool(descending)
    known = [row for row in rows if row.get(key) is not None]
    unknown = [row for row in rows if row.get(key) is None]
    if key in NUMERIC:
        known.sort(key=lambda row: row.get(key) or 0, reverse=reverse)
    else:
        known.sort(key=lambda row: str(row.get(key, "")).lower(), reverse=reverse)
    return known + unknown


@dataclass(frozen=True)
class Summary:
    """The header strip: the four meters Windows shows above the list."""

    cpu: str
    memory: str
    disk: str
    network: str
    uptime: str
    processes: int
    threads: int
    memory_detail: str


def summarise(snapshot) -> Summary:
    used = format_bytes(snapshot.memory_used)
    total = format_bytes(snapshot.memory_total) if snapshot.memory_total else DASH
    percent = snapshot.memory_percent
    return Summary(
        cpu=format_percent(snapshot.cpu),
        memory=DASH if percent is None else f"{percent} %",
        disk=(DASH if snapshot.disk_read_rate is None else
              f"{format_rate(snapshot.disk_read_rate)} / {format_rate(snapshot.disk_write_rate)}"),
        network=(DASH if snapshot.net_recv_rate is None else
                 f"{format_rate(snapshot.net_recv_rate)} / {format_rate(snapshot.net_sent_rate)}"),
        uptime=format_uptime(snapshot.uptime),
        processes=len(snapshot.processes),
        threads=sum(process.threads for process in snapshot.processes),
        memory_detail=f"{used} из {total}" if snapshot.memory_total else DASH,
    )


class History:
    """A fixed-length ring of readings for the graphs. Unknown samples are kept as None so a gap
    in measurement draws as a gap, not as a dip to zero."""

    def __init__(self, size: int = 60) -> None:
        self.size = size
        self._values: list[float | None] = []

    def push(self, value: float | None) -> None:
        self._values.append(value)
        if len(self._values) > self.size:
            del self._values[0:len(self._values) - self.size]

    @property
    def values(self) -> list[float | None]:
        return list(self._values)

    def points(self) -> list[float]:
        """What QML plots: known values only, so a missing sample breaks the line."""
        return [value for value in self._values if value is not None]
