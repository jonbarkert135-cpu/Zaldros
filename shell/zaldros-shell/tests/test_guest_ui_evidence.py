# SPDX-License-Identifier: GPL-3.0-or-later
"""Guest probes must prove a file/state change, not merely return a truthy object."""
import importlib.util
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("guest_probe", REPO / "build/iso/uitest.py")
guest = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guest)


@pytest.mark.parametrize("detail", [False, None, 0, [], "ERROR: failed", {},
                                    {"error": "no file"}, {"status": "PASS", "error": "no file"}])
def test_failure_values_never_become_successful_steps(monkeypatch, detail):
    class Sample:
        seconds, cpu, rss = 0, {}, {}
        def __enter__(self):
            return self
        def __exit__(self, *_):
            pass
    monkeypatch.setattr(guest, "Sampler", Sample)
    results = {}
    guest.step("probe", lambda: detail, results)
    assert results["probe"]["status"] == "FAIL"


def png(path):
    from PySide6.QtGui import QImage
    image = QImage(16, 8, QImage.Format_RGB32)
    image.fill(0xff123456)
    assert image.save(str(path))


@pytest.mark.parametrize("case", ["no-tool", "exit-error", "no-file", "invalid-image", "stale-file"])
def test_screenshot_requires_success_and_fresh_decodable_pixels(tmp_path, monkeypatch, case):
    target = tmp_path / "shot.png"
    if case == "stale-file":
        png(target)
    monkeypatch.setattr(guest.shutil, "which", lambda tool: tool if case != "no-tool" and tool == "spectacle" else None)
    def run(command, **kwargs):
        if case == "invalid-image":
            target.write_bytes(b"not an image")
        return subprocess.CompletedProcess(command, 1 if case == "exit-error" else 0,
                                           "", "ScreenShot2 is unavailable")
    monkeypatch.setattr(guest.subprocess, "run", run)
    with pytest.raises(RuntimeError):
        guest._screenshot(target)


def test_successful_screenshot_reports_image_dimensions(tmp_path, monkeypatch):
    target = tmp_path / "shot.png"
    monkeypatch.setattr(guest.shutil, "which", lambda tool: tool if tool == "spectacle" else None)
    def run(command, **kwargs):
        png(target)
        return subprocess.CompletedProcess(command, 0, "", "")
    monkeypatch.setattr(guest.subprocess, "run", run)
    result = guest._screenshot(target)
    assert result["tool"] == "spectacle" and result["bytes"] > 0
    assert (result["width"], result["height"]) == (16, 8)


def test_screenshot_error_preserves_backend_diagnostic(tmp_path, monkeypatch):
    monkeypatch.setattr(guest.shutil, "which", lambda _: "spectacle")
    monkeypatch.setattr(guest.subprocess, "run", lambda command, **_: subprocess.CompletedProcess(
        command, 1, "", "org.kde.KWin.ScreenShot2 interface missing"))
    with pytest.raises(RuntimeError, match="ScreenShot2 interface missing"):
        guest._screenshot(tmp_path / "shot.png")


@pytest.fixture
def window_probe(monkeypatch):
    monkeypatch.setattr(guest, "TEST_WINDOW_ID", "target")
    monkeypatch.setattr(guest.time, "sleep", lambda _: None)
    commands = []
    monkeypatch.setattr(guest, "_kwin_eval", commands.append)
    def readings(before, after):
        sequence = iter([before, after])
        monkeypatch.setattr(guest, "windows", lambda: next(sequence))
    return readings, commands


def window(identity="target", x=10, y=20, minimized=False):
    return dict(id=identity, caption="Home — Dolphin", x=x, y=y, minimized=minimized)


def test_move_requires_same_window_geometry_to_change(window_probe):
    readings, commands = window_probe
    readings([window()], [window(x=130, y=100)])
    result = guest._move()
    assert result["window_id"] == "target" and result["after"] == [130, 100]
    assert 'String(w.internalId) === "target"' in commands[0]


@pytest.mark.parametrize("after", [[window()], [window("other", x=130)], []])
def test_existing_or_other_window_does_not_prove_a_move(window_probe, after):
    readings, _ = window_probe
    readings([window()], after)
    assert guest._move() is False


@pytest.mark.parametrize("state", [True, False])
def test_minimize_and_restore_track_the_same_window_after_focus_changes(window_probe, state):
    readings, commands = window_probe
    readings([window(minimized=not state)], [window(minimized=state), window("other", minimized=not state)])
    result = guest._set_minimized(state)
    assert result["window_id"] == "target" and result["minimized"] is state
    assert 'String(w.internalId) === "target"' in commands[0]


def test_another_windows_state_cannot_prove_restore(window_probe):
    readings, _ = window_probe
    readings([window(minimized=True)], [window(minimized=True), window("other", minimized=False)])
    assert guest._set_minimized(False) is False


def test_an_already_matching_state_is_not_a_measured_transition(window_probe):
    readings, commands = window_probe
    readings([window(minimized=False)], [])
    assert guest._set_minimized(False) is False and not commands


def test_launched_window_identity_is_retained_for_later_probes(monkeypatch):
    monkeypatch.setattr(guest, "windows", lambda: [window()])
    monkeypatch.setattr(guest, "TEST_WINDOW_ID", None)
    result = guest.wait_for_window("dolphin", timeout=1)
    assert result["window_id"] == guest.TEST_WINDOW_ID == "target"
