# SPDX-License-Identifier: GPL-3.0-or-later
"""An Office gate must reject empty/partial/skipped suites, including collection skips."""
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "office.py"
spec = importlib.util.spec_from_file_location("office_ci", SCRIPT)
office = importlib.util.module_from_spec(spec)
spec.loader.exec_module(office)


@pytest.mark.parametrize("case, expected", [
    ("complete", 0), ("runtime-skip", 1), ("collection-skip", 1),
    ("only-ui", 1), ("only-engine", 1), ("empty", 5), ("assertion-failure", 1),
])
def test_actual_pytest_exit_requires_both_suites_without_skips(tmp_path, case, expected):
    passing = "def test_operation():\n    assert True\n"
    if case not in ("only-ui", "empty"):
        (tmp_path / "test_engine.py").write_text(
            'import pytest\npytest.skip("UNO absent", allow_module_level=True)\n'
            if case == "collection-skip" else
            'import pytest\ndef test_operation():\n    pytest.skip("UNO absent")\n'
            if case == "runtime-skip" else
            "def test_operation():\n    assert False\n"
            if case == "assertion-failure" else passing)
    if case not in ("only-engine", "empty"):
        (tmp_path / "test_ui.py").write_text(passing)
    command = (
        "import runpy,sys,pytest; "
        f"gate=runpy.run_path({str(SCRIPT)!r})['RequiredOfficeTests'](); "
        "sys.exit(pytest.main(['-q','.'],plugins=[gate]))")
    result = subprocess.run([sys.executable, "-c", command], cwd=tmp_path,
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == expected, result.stdout + result.stderr
    if expected == 1 and case != "assertion-failure":
        assert "Office acceptance FAIL" in result.stdout


def test_missing_uno_fails_before_tests_can_skip(tmp_path, monkeypatch, capsys):
    def unavailable(module):
        raise ModuleNotFoundError(f"No module named {module!r}")
    monkeypatch.setattr(office.importlib, "import_module", unavailable)
    assert office.main(["sheets", "--junitxml", str(tmp_path / "results.xml")]) == 1
    assert "Office preflight FAIL" in capsys.readouterr().err
    assert not (tmp_path / "results.xml").exists()


def test_no_executable_is_an_explicit_preflight_failure(monkeypatch):
    monkeypatch.setattr(office.importlib, "import_module", lambda _: None)
    monkeypatch.setattr(office.shutil, "which", lambda _: None)
    with pytest.raises(RuntimeError, match="not installed"):
        office.preflight()


def test_check_annotations_escape_workflow_commands(monkeypatch, capsys):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    print("...", end="")  # pytest's terminal progress must not prefix the command.
    office.annotate("error", "Office test failure", "100%\r\n::warning::embedded")
    assert capsys.readouterr().out == (
        "...\n::error title=Office test failure::100%25%0D%0A::warning::embedded\n")


def test_annotations_are_quiet_outside_actions(monkeypatch, capsys):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    office.annotate("notice", "Office test summary", "{}")
    assert not capsys.readouterr().out


def test_failure_annotation_keeps_actual_unicode_exception_before_long_source(tmp_path):
    (tmp_path / "test_engine.py").write_text(
        "def test_failure():\n" + "    # длинный исходный код\n" * 400
        + "    raise RuntimeError('DOCX round-trip diagnostic')\n")
    command = ("import runpy,sys,pytest; "
               f"gate=runpy.run_path({str(SCRIPT)!r})['RequiredOfficeTests'](); "
               "sys.exit(pytest.main(['-q','.'],plugins=[gate]))")
    import os
    result = subprocess.run([sys.executable, '-c', command], cwd=tmp_path,
                            capture_output=True, text=True, timeout=30,
                            env={**os.environ, 'GITHUB_ACTIONS': 'true'})
    assert result.returncode == 1
    annotation = next(line for line in result.stdout.splitlines()
                      if line.startswith('::error title=Office test failure::'))
    assert 'RuntimeError: DOCX round-trip diagnostic' in annotation[:250]
    assert len(annotation.encode('utf-8')) < 5000
