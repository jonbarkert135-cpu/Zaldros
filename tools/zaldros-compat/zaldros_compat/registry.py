"""Compatibility registries with evidence enforcement.

Implements spec PART 4 §3 (application compatibility classes) and §25 (hardware compatibility
states, "never claim universal hardware compatibility without evidence").

The rule this module enforces mechanically: a positive claim — an application marked
``compatible``/``partial`` or hardware marked ``tested``/``partially_tested`` — is invalid unless it
carries at least one evidence record with a date, a Zaldros build id and a tester. CI runs
``python -m zaldros_compat --check`` so an unevidenced claim fails the build instead of shipping.
"""

from __future__ import annotations

import datetime as _dt
import json
from dataclasses import dataclass, field

APP_CLASSES = ("native", "compatible", "partial", "unsupported", "untested")
APP_CLAIMS_NEEDING_EVIDENCE = ("compatible", "partial", "unsupported")
HW_STATES = ("tested", "partially_tested", "untested", "known_issue")
HW_CLAIMS_NEEDING_EVIDENCE = ("tested", "partially_tested", "known_issue")

REQUIRED_EVIDENCE_FIELDS = ("date", "build", "tester", "result")


@dataclass
class Evidence:
    date: str
    build: str
    tester: str
    result: str
    notes: str = ""


@dataclass
class Entry:
    """One application or one piece of hardware."""

    id: str
    name: str
    status: str
    kind: str  # "app" or "hardware"
    evidence: list[Evidence] = field(default_factory=list)
    notes: str = ""


class ValidationError(Exception):
    pass


def _valid_date(value: str) -> bool:
    try:
        _dt.date.fromisoformat(value)
    except (ValueError, TypeError):
        return False
    return True


def parse_entry(raw: dict, kind: str) -> Entry:
    for key in ("id", "name", "status"):
        if not raw.get(key):
            raise ValidationError(f"{kind} entry is missing required field '{key}': {raw!r}")
    allowed = APP_CLASSES if kind == "app" else HW_STATES
    if raw["status"] not in allowed:
        raise ValidationError(
            f"{kind} '{raw['id']}' has status '{raw['status']}', expected one of {allowed}"
        )
    evidence = []
    for item in raw.get("evidence", []):
        missing = [f for f in REQUIRED_EVIDENCE_FIELDS if not item.get(f)]
        if missing:
            raise ValidationError(
                f"{kind} '{raw['id']}' has an evidence record missing {missing}"
            )
        if not _valid_date(item["date"]):
            raise ValidationError(
                f"{kind} '{raw['id']}' has evidence with an invalid date '{item['date']}' "
                "(expected YYYY-MM-DD)"
            )
        evidence.append(
            Evidence(
                date=item["date"],
                build=item["build"],
                tester=item["tester"],
                result=item["result"],
                notes=item.get("notes", ""),
            )
        )
    return Entry(
        id=raw["id"],
        name=raw["name"],
        status=raw["status"],
        kind=kind,
        evidence=evidence,
        notes=raw.get("notes", ""),
    )


def needs_evidence(entry: Entry) -> bool:
    claims = APP_CLAIMS_NEEDING_EVIDENCE if entry.kind == "app" else HW_CLAIMS_NEEDING_EVIDENCE
    return entry.status in claims


def validate(entries: list[Entry]) -> list[str]:
    """Return a list of human-readable problems; empty means the registry is honest."""
    problems: list[str] = []
    seen: set[str] = set()
    for entry in entries:
        if entry.id in seen:
            problems.append(f"duplicate id '{entry.id}'")
        seen.add(entry.id)
        if needs_evidence(entry) and not entry.evidence:
            problems.append(
                f"{entry.kind} '{entry.id}' claims status '{entry.status}' with no evidence record — "
                "spec PART 4 §25 forbids compatibility claims without evidence"
            )
    return problems


def load(path: str, kind: str) -> list[Entry]:
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    raw_entries = data.get("entries", data if isinstance(data, list) else [])
    return [parse_entry(item, kind) for item in raw_entries]


def summarize(entries: list[Entry]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entry in entries:
        counts[entry.status] = counts.get(entry.status, 0) + 1
    return dict(sorted(counts.items()))


def to_markdown(entries: list[Entry], title: str) -> str:
    lines = [f"# {title}", "", f"Entries: **{len(entries)}**", ""]
    counts = summarize(entries)
    if counts:
        lines.append(" · ".join(f"{status}: **{count}**" for status, count in counts.items()))
        lines.append("")
    lines += ["| Item | Status | Evidence | Last test | Notes |", "| --- | --- | ---: | --- | --- |"]
    for entry in sorted(entries, key=lambda e: (e.status, e.id)):
        last = max((e.date for e in entry.evidence), default="—")
        lines.append(
            f"| {entry.name} (`{entry.id}`) | {entry.status} | {len(entry.evidence)} | {last} | "
            f"{entry.notes or '—'} |"
        )
    lines += [
        "",
        "> Statuses are claims backed by recorded test runs. `untested` is an honest answer and is "
        "always preferred over an unverified claim (spec PART 4 §3, §25).",
    ]
    return "\n".join(lines) + "\n"
