"""The shell must keep matching the measured Windows 11 geometry.

tools/visual/parity.py renders the shell, reads back the geometry of every named component and
compares it with system/theme/win11-reference.json. This test runs that comparison, so a layout
change that drifts away from Windows 11 fails CI instead of shipping.

It also guards the rule that Explorer and Settings are real applications: no placeholder copy.
"""
import os
import sys
from pathlib import Path

import pytest

pytest.importorskip("PySide6")

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "visual"))
sys.path.insert(0, str(ROOT / "shell" / "zaldros-shell"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import parity  # noqa: E402


@pytest.fixture(scope="module")
def checks(tmp_path_factory):
    directory = tmp_path_factory.mktemp("parity")
    geometry = parity.render_states(directory)
    reference = parity.json.loads(parity.REFERENCE.read_text())
    return parity.collect_checks(geometry, reference)


def test_every_component_matches_the_windows_11_reference(checks):
    failures = [check.line() for check in checks if not check.passed]
    assert not failures, "components drifted from the reference:\n" + "\n".join(failures)


def test_the_reference_covers_every_reworked_component(checks):
    covered = {check.component for check in checks}
    assert covered >= {"taskbar", "start", "window", "explorer", "settings",
                       "quick settings", "notifications", "context menu"}


PLACEHOLDER_PHRASES = ("ещё не реализован", "макет оформления", "Lorem", "TODO", "заглушка")


@pytest.mark.parametrize("name", ["apps/Explorer.qml", "apps/Settings.qml"])
def test_applications_carry_no_placeholder_copy(name):
    source = (ROOT / "shell" / "zaldros-shell" / "qml" / name).read_text(encoding="utf-8")
    found = [phrase for phrase in PLACEHOLDER_PHRASES if phrase in source]
    assert not found, f"{name} still contains placeholder copy: {found}"
