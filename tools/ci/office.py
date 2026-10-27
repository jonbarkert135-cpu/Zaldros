#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Run a mandatory Office suite with this interpreter's real UNO/Qt runtime."""
from __future__ import annotations

import argparse
import importlib
import json
import os
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APPS = ("writer", "sheets", "slides")


def annotate(level, title, message):
    """Expose bounded diagnostics through the Checks API as well as artifact logs."""
    if os.environ.get("GITHUB_ACTIONS") == "true":
        escaped = str(message).replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
        # pytest writes progress without a newline; runner commands must start one.
        print(f"\n::{level} title={title}::{escaped}", flush=True)


class RequiredOfficeTests:
    """A green job requires executed engine and UI tests, with no hidden skips."""

    def __init__(self):
        self.skipped = []
        self.passed = Counter()

    def pytest_collectreport(self, report):
        if report.skipped:
            self.skipped.append(report.nodeid)
        if report.failed:
            annotate("error", "Office collection failure", str(report.longrepr)[-5000:])

    def pytest_runtest_logreport(self, report):
        if report.skipped:
            self.skipped.append(report.nodeid)
        if report.failed:
            # Put the actual exception first. Long Unicode source excerpts can use
            # the annotation's byte budget before the assertion is ever visible.
            crash = getattr(report.longrepr, "reprcrash", None)
            detail = f"{crash.message}\n{report.nodeid}" if crash else str(report.longrepr)
            annotate("error", "Office test failure", detail.encode("utf-8")[:4500].decode("utf-8", errors="ignore"))
        if report.when == "call" and report.passed:
            self.passed[Path(report.nodeid.split("::", 1)[0]).name] += 1

    def pytest_sessionfinish(self, session, exitstatus):
        missing = {"test_engine.py", "test_ui.py"} - self.passed.keys()
        if exitstatus == 0 and (self.skipped or missing):
            session.exitstatus = 1
            terminal = session.config.pluginmanager.get_plugin("terminalreporter")
            if terminal:
                terminal.write_line(
                    f"Office acceptance FAIL: {len(self.skipped)} skipped; "
                    f"missing executed suites: {sorted(missing)}", red=True)
        annotate("notice", "Office test summary", json.dumps({
            "collected": session.testscollected, "passed": dict(self.passed),
            "failed": session.testsfailed, "skipped": len(self.skipped),
            "exitstatus": int(session.exitstatus)}))


def preflight():
    """Do not confuse an executable on PATH with a working Python bridge."""
    for module in ("uno", "PySide6.QtGui", "PySide6.QtQml", "PySide6.QtQuick", "pytest"):
        importlib.import_module(module)
    binary = shutil.which("soffice") or shutil.which("libreoffice")
    if not binary:
        raise RuntimeError("LibreOffice is not installed (no soffice/libreoffice on PATH)")
    print(f"Office interpreter: {sys.executable}\nLibreOffice executable: {binary}", flush=True)
    if os.environ.get("GITHUB_ACTIONS") == "true":
        version = subprocess.check_output([binary, "--version"], text=True, timeout=10).strip()
        annotate("notice", "Office runtime", json.dumps({
            "python": sys.version.split()[0], "libreoffice": version,
            "uno_module": importlib.import_module("uno").__file__,
            "workflow_sha": os.environ.get("GITHUB_SHA"),
            "run_id": os.environ.get("GITHUB_RUN_ID")}))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app", choices=APPS)
    parser.add_argument("--junitxml", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        preflight()
    except (ImportError, RuntimeError, OSError, subprocess.SubprocessError) as exc:
        print(f"Office preflight FAIL: {exc}. Use the system Python matching python3-uno "
              "and a venv with --system-site-packages.", file=sys.stderr)
        return 1
    import pytest

    args.junitxml.parent.mkdir(parents=True, exist_ok=True)
    return int(pytest.main([str(ROOT / "apps" / args.app / "tests"), "-q", "-ra", "--tb=short",
                            f"--junitxml={args.junitxml.resolve()}"],
                           plugins=[RequiredOfficeTests()]))


if __name__ == "__main__":
    raise SystemExit(main())
