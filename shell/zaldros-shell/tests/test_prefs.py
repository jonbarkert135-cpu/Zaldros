"""Settings switches must really switch, and survive a reboot.

Every switch in Settings used to be a painted rectangle with a hard-coded value. These tests hold
the line for the ones that are now real: they are stored on disk, read back, and reach both the
Settings tree and the taskbar.
"""

from __future__ import annotations

from pathlib import Path

from zaldros_shell import prefs, settingspages


def test_defaults_are_returned_when_nothing_was_ever_saved(tmp_path: Path) -> None:
    values = prefs.load(tmp_path)
    assert values == prefs.DEFAULTS
    assert not prefs.config_path(tmp_path).exists(), "reading must not create a file"


def test_a_switch_survives_the_session(tmp_path: Path) -> None:
    assert prefs.set_value("taskbar.search", False, tmp_path) is True
    assert prefs.load(tmp_path)["taskbar.search"] is False
    assert prefs.load(tmp_path)["taskbar.clock"] is True, "the others must not move"
    text = prefs.config_path(tmp_path).read_text(encoding="utf-8")
    assert "taskbar.search=false" in text


def test_unknown_keys_are_refused_not_invented(tmp_path: Path) -> None:
    assert prefs.set_value("taskbar.unicorn", True, tmp_path) is False
    assert not prefs.config_path(tmp_path).exists()


def test_foreign_keys_in_the_file_are_kept(tmp_path: Path) -> None:
    path = prefs.config_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("future.option=true\ntaskbar.clock=false\n", encoding="utf-8")
    prefs.set_value("taskbar.search", False, tmp_path)
    text = path.read_text(encoding="utf-8")
    assert "future.option=true" in text, "a newer session's setting must not be destroyed"
    assert "taskbar.clock=false" in text


def test_a_corrupt_line_falls_back_to_the_default(tmp_path: Path) -> None:
    path = prefs.config_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("taskbar.clock=maybe\nnonsense\n", encoding="utf-8")
    assert prefs.load(tmp_path)["taskbar.clock"] is True


def test_the_settings_tree_shows_the_stored_state_not_a_constant() -> None:
    switches = dict(prefs.DEFAULTS, **{"taskbar.search": False})
    tree = settingspages.to_variant(settingspages.build(switches=switches))
    rows = [entry for page in tree.values() for entry in page["entries"]
            if entry.get("pref") == "taskbar.search"]
    assert rows, "the search switch must be reachable in Settings"
    assert rows[0]["toggle"] is False
    assert rows[0]["hasToggle"] is True


def test_every_pref_backed_row_names_a_key_we_implement() -> None:
    tree = settingspages.to_variant(settingspages.build())
    keys = {entry["pref"] for page in tree.values() for entry in page["entries"]
            if entry.get("pref")}
    assert keys, "the tree must expose the switches that work"
    assert keys <= set(prefs.DEFAULTS), f"unimplemented switch keys: {keys - set(prefs.DEFAULTS)}"


def test_the_taskbar_hides_what_the_user_switched_off() -> None:
    qml = (Path(__file__).resolve().parents[1] / "qml" / "Taskbar.qml").read_text(encoding="utf-8")
    for key in ("taskbar.search", "taskbar.widgets", "taskbar.taskview", "taskbar.clock"):
        assert f'shown("{key}")' in qml, f"{key} must control something visible"
    assert 'typeof prefs !== "undefined"' in qml, (
        "the renderer loads the taskbar without the shell context; it must still draw"
    )


def test_start_hides_its_recommendations_when_the_switch_is_off() -> None:
    """Персонализация > Пуск > «Недавние файлы» is a real switch: it must reach the section it
    names, header and empty state included, or the Start panel keeps a stray heading."""
    qml = (Path(__file__).resolve().parents[1] / "qml" / "StartMenu.qml").read_text(encoding="utf-8")
    assert qml.count('shown_("start.recent")') == 3, (
        "the header, the grid and the empty-state text all belong to that section"
    )
    assert 'typeof prefs !== "undefined"' in qml, (
        "the offscreen renderer has no prefs context; Start must still draw"
    )
