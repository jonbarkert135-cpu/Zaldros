#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Run a mandatory Office suite with this interpreter's real UNO/Qt runtime."""
from __future__ import annotations

import argparse
import importlib
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APPS = ("writer", "sheets", "slides")


class RequiredOfficeTests:
    """A green job requires executed engine and UI tests, with no hidden skips."""

    def __init__(self):
        self.skipped = []
        self.passed = set()

    def pytest_collectreport(self, report):
        if report.skipped:
            self.skipped.append(report.nodeid)

    def pytest_runtest_logreport(self, report):
        if report.skipped:
            self.skipped.append(report.nodeid)
        if report.when == "call" and report.passed:
            self.passed.add(Path(report.nodeid.split("::", 1)[0]).name)

    def pytest_sessionfinish(self, session, exitstatus):
        missing = {"test_engine.py", "test_ui.py"} - self.passed
        if exitstatus == 0 and (self.skipped or missing):
            session.exitstatus = 1
            terminal = session.config.pluginmanager.get_plugin("terminalreporter")
            if terminal:
                terminal.write_line(
                    f"Office acceptance FAIL: {len(self.skipped)} skipped; "
                    f"missing executed suites: {sorted(missing)}", red=True)


def preflight():
    """Do not confuse an executable on PATH with a working Python bridge."""
    for module in ("uno", "PySide6.QtGui", "PySide6.QtQml", "PySide6.QtQuick", "pytest"):
        importlib.import_module(module)
    binary = shutil.which("soffice") or shutil.which("libreoffice")
    if not binary:
        raise RuntimeError("LibreOffice is not installed (no soffice/libreoffice on PATH)")
    print(f"Office interpreter: {sys.executable}\nLibreOffice executable: {binary}", flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app", choices=APPS)
    parser.add_argument("--junitxml", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        preflight()
    except (ImportError, RuntimeError, OSError) as exc:
        print(f"Office preflight FAIL: {exc}. Use the system Python matching python3-uno "
              "and a venv with --system-site-packages.", file=sys.stderr)
        return 1
    import pytest

    args.junitxml.parent.mkdir(parents=True, exist_ok=True)
    return int(pytest.main([str(ROOT / "apps" / args.app / "tests"), "-q", "-ra",
                            f"--junitxml={args.junitxml.resolve()}"],
                           plugins=[RequiredOfficeTests()]))


if __name__ == "__main__":
    raise SystemExit(main())
