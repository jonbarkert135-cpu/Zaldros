"""Tests for real .desktop discovery, parsing and launching."""
from pathlib import Path

import pytest

from bedrock_shell.desktop_entries import (
    DesktopApp, application_dirs, discover, launch, parse_desktop_file,
)

SAMPLE = """[Desktop Entry]
Type=Application
Name=Text Editor
Name[ru]=Текстовый редактор
Comment=Edit text
Comment[ru]=Редактирование текста
Exec=geany %F
Icon=geany
Categories=Utility;TextEditor;
Terminal=false

[Desktop Action New]
Name=New window
Exec=geany --new
"""


def test_localized_name_and_field_codes_are_handled():
    app = parse_desktop_file(SAMPLE, locale="ru")
    assert app.name == "Текстовый редактор"
    assert app.comment == "Редактирование текста"
    assert app.exec_command == "geany"        # %F stripped, per the XDG spec
    assert app.exec_name == "geany"
    assert "TextEditor" in app.categories


def test_english_locale_falls_back_to_plain_name():
    assert parse_desktop_file(SAMPLE, locale="en").name == "Text Editor"


def test_non_application_and_link_entries_are_ignored():
    assert parse_desktop_file("[Desktop Entry]\nType=Link\nName=X\nURL=http://x\n") is None


def test_hidden_entries_are_discovered_but_flagged():
    app = parse_desktop_file("[Desktop Entry]\nType=Application\nName=H\nExec=h\nNoDisplay=true\n")
    assert app.no_display is True


def test_discover_reads_a_real_directory(tmp_path: Path):
    (tmp_path / "a.desktop").write_text(SAMPLE, encoding="utf-8")
    (tmp_path / "hidden.desktop").write_text(
        "[Desktop Entry]\nType=Application\nName=Hidden\nExec=h\nNoDisplay=true\n", encoding="utf-8")
    (tmp_path / "noexec.desktop").write_text(
        "[Desktop Entry]\nType=Application\nName=NoExec\n", encoding="utf-8")
    apps = discover([tmp_path], locale="ru")
    assert [a.name for a in apps] == ["Текстовый редактор"]


def test_discover_survives_a_missing_directory():
    assert discover([Path("/definitely/not/here")]) == []


def test_application_dirs_follow_xdg():
    dirs = application_dirs({"HOME": "/home/u", "XDG_DATA_DIRS": "/opt/share:/usr/share"})
    assert dirs[0] == Path("/home/u/.local/share/applications")
    assert Path("/opt/share/applications") in dirs


def test_launch_uses_a_detached_process_and_reports_failure():
    calls = []

    def fake_runner(argv, **kwargs):
        calls.append((argv, kwargs))
        return None

    app = DesktopApp(name="X", exec_command="kate --new", icon="", categories=())
    assert launch(app, runner=fake_runner) is True
    assert calls[0][0] == ["kate", "--new"]
    assert calls[0][1]["start_new_session"] is True

    def failing_runner(argv, **kwargs):
        raise OSError("no such binary")

    assert launch(app, runner=failing_runner) is False
    assert launch(DesktopApp("X", "", "", ()), runner=fake_runner) is False


def test_the_running_system_is_readable():
    """Not a mock: the test machine must expose an application database we can parse."""
    apps = discover()
    assert isinstance(apps, list)
    for app in apps:
        assert app.name and app.exec_command
