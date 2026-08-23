import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bedrock_compat.registry import (  # noqa: E402
    Entry,
    Evidence,
    ValidationError,
    load,
    needs_evidence,
    parse_entry,
    summarize,
    to_markdown,
    validate,
)
from bedrock_compat.__main__ import main  # noqa: E402

DATA = os.path.join(os.path.dirname(__file__), "..", "data")

GOOD_EVIDENCE = {
    "date": "2026-08-23",
    "build": "bedrock-0.1.0-20260823",
    "tester": "ci",
    "result": "installs and runs",
}


def test_parse_entry_rejects_unknown_status():
    with pytest.raises(ValidationError):
        parse_entry({"id": "x", "name": "X", "status": "works-probably"}, "app")


def test_parse_entry_requires_core_fields():
    with pytest.raises(ValidationError):
        parse_entry({"name": "X", "status": "untested"}, "app")


def test_evidence_must_be_complete_and_dated():
    base = {"id": "x", "name": "X", "status": "compatible"}
    with pytest.raises(ValidationError):
        parse_entry({**base, "evidence": [{"date": "2026-08-23", "build": "b"}]}, "app")
    with pytest.raises(ValidationError):
        parse_entry({**base, "evidence": [{**GOOD_EVIDENCE, "date": "23.08.2026"}]}, "app")
    entry = parse_entry({**base, "evidence": [GOOD_EVIDENCE]}, "app")
    assert entry.evidence[0].build == "bedrock-0.1.0-20260823"


def test_needs_evidence_rules():
    assert needs_evidence(Entry("a", "A", "compatible", "app")) is True
    assert needs_evidence(Entry("a", "A", "partial", "app")) is True
    assert needs_evidence(Entry("a", "A", "native", "app")) is False
    assert needs_evidence(Entry("a", "A", "untested", "app")) is False
    assert needs_evidence(Entry("h", "H", "tested", "hardware")) is True
    assert needs_evidence(Entry("h", "H", "known_issue", "hardware")) is True
    assert needs_evidence(Entry("h", "H", "untested", "hardware")) is False


def test_validate_flags_unevidenced_claim():
    problems = validate([Entry("gpu", "GPU", "tested", "hardware")])
    assert len(problems) == 1
    assert "no evidence record" in problems[0]


def test_validate_accepts_evidenced_claim():
    entry = Entry("gpu", "GPU", "tested", "hardware", evidence=[Evidence(**GOOD_EVIDENCE)])
    assert validate([entry]) == []


def test_validate_detects_duplicate_ids():
    entries = [Entry("a", "A", "untested", "app"), Entry("a", "A2", "untested", "app")]
    assert any("duplicate" in problem for problem in validate(entries))


def test_summarize_and_markdown():
    entries = [
        Entry("a", "A", "untested", "app"),
        Entry("b", "B", "native", "app"),
        Entry("c", "C", "native", "app"),
    ]
    assert summarize(entries) == {"native": 2, "untested": 1}
    report = to_markdown(entries, "Title")
    assert "# Title" in report and "native: **2**" in report and "`a`" in report


def test_shipped_registries_are_valid_and_honest():
    for filename, kind in (("applications.json", "app"), ("hardware.json", "hardware")):
        entries = load(os.path.join(DATA, filename), kind)
        assert entries, f"{filename} is empty"
        assert validate(entries) == []


def test_cli_check_passes_on_shipped_data(capsys):
    assert main(["--check", "--data-dir", DATA]) == 0


def test_cli_check_fails_on_unevidenced_claim(tmp_path):
    for filename, payload in (
        ("applications.json", {"entries": []}),
        ("hardware.json", {"entries": [{"id": "gpu", "name": "GPU", "status": "tested"}]}),
    ):
        (tmp_path / filename).write_text(json.dumps(payload), encoding="utf-8")
    assert main(["--check", "--data-dir", str(tmp_path)]) == 1
