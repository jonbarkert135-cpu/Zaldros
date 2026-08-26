"""Guard: a report quoted inside another report must never be mistaken for the real one.

Run #34 (iso 33020297733): the late report embeds the session log, the session log contained
an echoed `ZALDROS-SELFTEST {...}` line, and the host extracted that *escaped* copy with
`grep -o ... | tail -1`. `{\\"kernel\\"` is not JSON, so every boot job died with
JSONDecodeError and a fully successful boot was reported as a failed build.

Two defences, both tested here: the guest never emits a nested marker, and the host only
accepts a candidate that parses.
"""

import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
ISO = REPO / "build" / "iso"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ISO / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


extract_marked = _load("extract_marked")
selftest = _load("selftest")


def test_the_guest_never_nests_a_marker_inside_a_report():
    line = selftest.marked(
        selftest.LATE_MARK,
        {"session_log_tail": 'noise ZALDROS-SELFTEST {"kernel": "6.14"} more noise',
         "tabbox_lines": ["ZALDROS-UITEST {}"]},
    )
    body = line[len(selftest.LATE_MARK):]
    for mark in (selftest.MARK, selftest.UITEST_MARK, selftest.GEOMETRY_MARK,
                 selftest.LATE_MARK):
        assert mark.strip() not in body
    payload = json.loads(body)                      # still one valid JSON object
    assert "kernel" in payload["session_log_tail"]  # the evidence survives, only renamed


def test_the_host_skips_an_escaped_copy_and_takes_the_real_report(tmp_path):
    real = {"kernel": "6.14.0-zaldros", "boot": "real"}
    serial = "\n".join([
        "[    0.00] Linux version ...",
        'ZALDROS-SELFTEST ' + json.dumps(real),
        # a later line quoting an older report, exactly as the late report used to do
        'ZALDROS-LATE {"session_log_tail": "ZALDROS-SELFTEST {\\"kernel\\": \\"quoted\\"}"}',
        "ubuntu login: ",
    ])
    log = tmp_path / "serial.log"
    log.write_text(serial)

    out = tmp_path / "boot.json"
    assert extract_marked.main.__module__                       # loaded, not stubbed
    data = extract_marked.extract(log.read_text(), "ZALDROS-SELFTEST ")
    assert data == real

    # and the late report itself is still recoverable
    late = extract_marked.extract(log.read_text(), "ZALDROS-LATE ")
    assert "session_log_tail" in late
    assert not out.exists()


def test_the_boot_script_extracts_reports_by_parsing_not_by_grep():
    script = (ISO / "boot-test.sh").read_text()
    assert "extract_marked.py" in script
    assert "cut -c18-" not in script     # the fragile offset trick is gone for good
    assert "ZALDROS-LATE" in script      # the late report lands in the artifact too
