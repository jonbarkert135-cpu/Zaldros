"""Win+G: the capture panel must only promise what this machine can do.

The rule under test is the one that separates a desktop from a screenshot of one — a tile whose
tool is not installed is disabled and says why, a screenshot counts as taken only when the file is
on disk, and a recording command is never built without a real PipeWire node to read from.
"""

from pathlib import Path

import pytest

from zaldros_shell import capture
from zaldros_shell.model import GameBarModel


# --- where the files go ---------------------------------------------------------------------
def test_captures_follow_the_xdg_user_directories(tmp_path, monkeypatch):
    monkeypatch.delenv("XDG_PICTURES_DIR", raising=False)
    monkeypatch.delenv("XDG_VIDEOS_DIR", raising=False)
    conf = tmp_path / ".config"
    conf.mkdir()
    (conf / "user-dirs.dirs").write_text(
        'XDG_PICTURES_DIR="$HOME/Изображения"\nXDG_VIDEOS_DIR="$HOME/Видео"\n', encoding="utf-8")
    assert capture.screenshots_dir(tmp_path) == tmp_path / "Изображения/Zaldros/Снимки экрана"
    assert capture.recordings_dir(tmp_path) == tmp_path / "Видео/Zaldros/Записи"


def test_without_user_dirs_the_english_defaults_are_used(tmp_path, monkeypatch):
    monkeypatch.delenv("XDG_PICTURES_DIR", raising=False)
    assert capture.screenshots_dir(tmp_path) == tmp_path / "Pictures/Zaldros/Снимки экрана"


def test_file_names_carry_the_moment_they_were_taken():
    assert capture.screenshot_name(0).startswith("Снимок ")
    assert capture.screenshot_name(0).endswith(".png")
    assert capture.recording_name(0).endswith(".mp4")


# --- the commands ----------------------------------------------------------------------------
def test_the_screenshot_command_writes_where_we_asked(tmp_path):
    target = tmp_path / "shot.png"
    spectacle = capture.screenshot_command(target, capture.Tool("spectacle", "spectacle", ""))
    assert spectacle[0] == "spectacle" and str(target) in spectacle
    grim = capture.screenshot_command(target, capture.Tool("grim", "grim", ""))
    assert grim == ["grim", str(target)]


def test_no_grabber_means_no_command_and_a_reason(monkeypatch, tmp_path):
    monkeypatch.setattr(capture, "which", lambda _b: None)
    assert capture.pick(capture.SCREENSHOT_TOOLS) is None
    assert capture.screenshot_command(tmp_path / "x.png") is None
    assert "spectacle" in capture.missing_reason("screenshot")


def test_recording_without_a_pipewire_node_is_refused(tmp_path):
    """A command with no node would record a black rectangle and call it a video."""
    ffmpeg = capture.Tool("ffmpeg", "ffmpeg", "")
    assert capture.recording_command(tmp_path / "v.mp4", node=None, tool=ffmpeg) is None
    cmd = capture.recording_command(tmp_path / "v.mp4", node=42, fd=7, tool=ffmpeg)
    assert "pipewiregrab=node=42:fd=7" in cmd
    assert cmd[-1] == str(tmp_path / "v.mp4")


def test_the_microphone_only_adds_audio_when_it_is_on(tmp_path):
    ffmpeg = capture.Tool("ffmpeg", "ffmpeg", "")
    silent = capture.recording_command(tmp_path / "v.mp4", node=1, tool=ffmpeg)
    loud = capture.recording_command(tmp_path / "v.mp4", node=1, tool=ffmpeg,
                                     with_microphone=True)
    assert "pulse" not in silent and "pulse" in loud


@pytest.mark.parametrize("seconds,text", [(0, "0:00"), (9, "0:09"), (75, "1:15"), (3671, "1:01:11")])
def test_the_timer_reads_like_a_stopwatch(seconds, text):
    assert capture.elapsed_text(seconds) == text


# --- the model -------------------------------------------------------------------------------
class FakeProcess:
    def __init__(self, command, target: Path | None = None, write=True):
        self.command = command
        self.terminated = False
        if write and target is not None:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"\x89PNG")

    def wait(self, timeout=None):
        return 0

    def terminate(self):
        self.terminated = True


def _model(tmp_path, monkeypatch, tools=("spectacle", "ffmpeg"), write=True):
    monkeypatch.setenv("XDG_PICTURES_DIR", str(tmp_path / "pic"))
    monkeypatch.setenv("XDG_VIDEOS_DIR", str(tmp_path / "vid"))
    monkeypatch.setattr(capture, "which", lambda b: f"/usr/bin/{b}" if b in tools else None)
    seen = []

    def runner(command):
        seen.append(command)
        return FakeProcess(command, Path(command[-1]), write=write)

    model = GameBarModel(runner=runner)
    return model, seen


def test_a_screenshot_is_only_reported_when_the_file_exists(tmp_path, monkeypatch):
    model, seen = _model(tmp_path, monkeypatch)
    assert model.canScreenshot is True
    assert model.takeScreenshot() is True
    assert seen[0][0] == "spectacle"
    assert Path(model.lastFile).is_file()
    assert "Снимок сохранён" in model.status


def test_a_grabber_that_writes_nothing_is_a_failure_not_a_success(tmp_path, monkeypatch):
    model, _seen = _model(tmp_path, monkeypatch, write=False)
    assert model.takeScreenshot() is False
    assert "не создал файл" in model.status


def test_without_any_grabber_the_tile_is_off_and_explains_itself(tmp_path, monkeypatch):
    model, seen = _model(tmp_path, monkeypatch, tools=())
    assert model.canScreenshot is False and model.canRecord is False
    assert model.takeScreenshot() is False
    assert seen == []
    assert "недоступен" in model.status


def test_recording_needs_the_portal_and_says_so_when_it_is_absent(tmp_path, monkeypatch):
    from zaldros_shell import portal

    model, seen = _model(tmp_path, monkeypatch)

    def refuse():
        raise portal.PortalError("xdg-desktop-portal не запущен: записывать экран нечем")

    monkeypatch.setattr(portal, "session", refuse)
    assert model.startRecording() is False
    assert model.recording is False
    assert seen == []
    assert "xdg-desktop-portal" in model.status


def test_a_recording_runs_ffmpeg_on_the_node_the_portal_gave_us(tmp_path, monkeypatch):
    from zaldros_shell import portal

    model, seen = _model(tmp_path, monkeypatch)
    monkeypatch.setattr(portal, "session", lambda: portal.Cast(node=7, fd=11, session="/s"))
    assert model.startRecording() is True
    assert model.recording is True
    assert "pipewiregrab=node=7:fd=11" in seen[0]
    assert model.stopRecording() is True
    assert model.recording is False


def test_the_microphone_starts_muted_like_the_windows_widget(tmp_path, monkeypatch):
    model, _ = _model(tmp_path, monkeypatch)
    assert model.micEnabled is False
    assert model.toggleMic() is True
    assert model.micEnabled is True


# --- the flyout ------------------------------------------------------------------------------
REPO = Path(__file__).resolve().parents[3]
QML = (REPO / "shell" / "zaldros-shell" / "qml" / "GameBarFlyout.qml").read_text()
SHELL_QML = (REPO / "shell" / "zaldros-shell" / "qml" / "Shell.qml").read_text()


def test_every_tile_is_wired_to_the_real_capture_model():
    assert "flyout.capture.takeScreenshot()" in QML
    assert "flyout.capture.toggleRecording()" in QML
    assert "flyout.capture.toggleMic()" in QML
    assert "flyout.capture.openCaptures()" in QML
    assert "ListModel" not in QML                 # nothing here is sample data


def test_a_tile_without_a_tool_is_disabled_and_the_reason_is_on_screen():
    assert "available: flyout.capture ? flyout.capture.canScreenshot : false" in QML
    assert "available: flyout.capture ? flyout.capture.canRecord : false" in QML
    assert 'objectName: "gameBarStatus"' in QML and "flyout.capture.status" in QML


def test_win_g_opens_it_and_closes_the_other_flyouts():
    assert '"Meta+G"' in SHELL_QML
    assert "shell.gameBarOpen = false;" in SHELL_QML.split("function closeAllFlyouts")[1]


def test_the_panel_keeps_the_measured_windows_geometry():
    import json
    reference = json.loads((REPO / "system" / "theme" / "win11-reference.json").read_text())
    theme = (REPO / "shell" / "zaldros-shell" / "qml" / "ZaldrosTheme" / "Theme.qml").read_text()
    bar = reference["game_bar"]
    assert f"gameBarWidth:      {bar['width']}" in theme
    assert f"gameBarTile:        {bar['tile']}" in theme
    assert f"gameBarTileGap:     {bar['tile_gap']}" in theme
    # 17 + 4 tiles + 3 gaps + 17 is exactly the measured 306
    assert 2 * bar["padding"] + 4 * bar["tile"] + 3 * bar["tile_gap"] == bar["width"]


def test_the_boot_test_really_takes_a_screenshot_in_the_guest():
    uitest = (REPO / "build" / "iso" / "uitest.py").read_text()
    assert 'step("screenshot"' in uitest
    assert "the tool ran but wrote no file" in uitest
    report = (REPO / "build" / "iso" / "report.py").read_text()
    assert '"screenshot"' in report


def test_the_image_ships_a_grabber_so_the_tile_is_not_dead_on_arrival():
    build = (REPO / "build" / "iso" / "build-iso.sh").read_text()
    assert "kde-spectacle" in build and "xdg-desktop-portal" in build and "ffmpeg" in build
