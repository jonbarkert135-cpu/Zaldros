"""The file manager works on the real filesystem, so its operations are tested against one.

The contract: nothing is invented, nothing is overwritten, and deleting means the freedesktop bin
every other Linux file manager reads — not an unrecoverable unlink.
"""
import urllib.parse
from pathlib import Path

from zaldros_shell import files


def test_listing_puts_folders_first_then_files_alphabetically(tmp_path: Path):
    (tmp_path / "zebra.txt").write_text("x")
    (tmp_path / "Album").mkdir()
    (tmp_path / "apple.txt").write_text("x")
    (tmp_path / ".hidden").write_text("x")
    names = [entry.name for entry in files.list_directory(tmp_path)]
    assert names == ["Album", "apple.txt", "zebra.txt"], "Windows Explorer order, hidden excluded"


def test_creating_a_folder_never_overwrites_the_previous_one(tmp_path: Path):
    first = files.create_folder(tmp_path)
    second = files.create_folder(tmp_path)
    assert first.ok and second.ok
    assert Path(first.path).name == "Новая папка"
    assert Path(second.path).name == "Новая папка (2)", "Windows counts, it does not clobber"
    assert Path(first.path).is_dir() and Path(second.path).is_dir()


def test_rename_refuses_an_empty_name_a_slash_and_an_occupied_name(tmp_path: Path):
    source = tmp_path / "note.txt"
    source.write_text("x")
    (tmp_path / "taken.txt").write_text("x")
    assert not files.rename(source, "  ").ok
    assert not files.rename(source, "a/b").ok
    assert not files.rename(source, "taken.txt").ok
    assert source.exists(), "a refused rename leaves the file alone"
    result = files.rename(source, "заметка.txt")
    assert result.ok and Path(result.path).name == "заметка.txt" and not source.exists()


def test_delete_moves_the_file_into_the_freedesktop_bin_with_a_restore_record(tmp_path: Path):
    home = tmp_path / "home"
    (home / "Documents").mkdir(parents=True)
    victim = home / "Documents" / "отчёт.txt"
    victim.write_text("данные")

    result = files.move_to_trash(victim, home=home)

    assert result.ok and not victim.exists(), "the file left its folder"
    trashed = Path(result.path)
    assert trashed.parent == home / ".local/share/Trash/files"
    assert trashed.read_text() == "данные", "the contents survive the trip"

    info = (home / ".local/share/Trash/info" / (trashed.name + ".trashinfo")).read_text()
    assert info.startswith("[Trash Info]")
    recorded = [line[5:] for line in info.splitlines() if line.startswith("Path=")][0]
    assert urllib.parse.unquote(recorded) == str(victim.resolve()), "restorable to where it was"
    assert any(line.startswith("DeletionDate=") for line in info.splitlines())


def test_deleting_two_files_of_the_same_name_keeps_both_in_the_bin(tmp_path: Path):
    home = tmp_path / "home"
    for folder in ("a", "b"):
        (home / folder).mkdir(parents=True)
        (home / folder / "same.txt").write_text(folder)
    first = files.move_to_trash(home / "a" / "same.txt", home=home)
    second = files.move_to_trash(home / "b" / "same.txt", home=home)
    assert first.ok and second.ok
    assert Path(first.path).name != Path(second.path).name, "the bin does not swallow a namesake"
    assert Path(first.path).read_text() == "a" and Path(second.path).read_text() == "b"


def test_deleting_something_that_is_already_gone_reports_it(tmp_path: Path):
    result = files.move_to_trash(tmp_path / "ghost.txt", home=tmp_path)
    assert not result.ok and result.error


def test_human_size_uses_the_units_windows_uses(tmp_path: Path):
    assert files.human_size(0, is_dir=True) == "", "folders show no size in Explorer"
    assert files.human_size(2048, is_dir=False) == "2 КБ"
    assert files.human_size(5 * 1024 ** 2, is_dir=False) == "5 МБ"


# --- the model the QML talks to ---------------------------------------------------------------

def _model(path):
    from zaldros_shell.model import FileModel
    return FileModel(str(path))


def test_the_model_creates_selects_and_renames_a_folder(tmp_path):
    model = _model(tmp_path)
    created = model.createFolder()
    assert created and Path(created).is_dir()
    row = model.rowForPath(created)
    assert row >= 0, "the view needs the row to select and rename it, as Explorer does"
    assert model.renameRow(row, "Проекты")
    assert (tmp_path / "Проекты").is_dir() and not Path(created).exists()
    assert model.errorText == ""


def test_a_refused_rename_reaches_the_user_as_a_sentence(tmp_path):
    (tmp_path / "a.txt").write_text("x")
    (tmp_path / "b.txt").write_text("x")
    model = _model(tmp_path)
    row = model.rowForPath(str(tmp_path / "a.txt"))
    assert not model.renameRow(row, "b.txt")
    assert "уже существует" in model.errorText
    assert (tmp_path / "a.txt").exists(), "both files are still there"


def test_the_model_deletes_into_the_bin_and_the_row_disappears(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("XDG_DATA_HOME", str(home / ".local/share"))
    (tmp_path / "old.log").write_text("x")
    model = _model(tmp_path)
    assert model.deleteRow(model.rowForPath(str(tmp_path / "old.log")))
    assert model.rowForPath(str(tmp_path / "old.log")) == -1, "the listing refreshed"
    assert (home / ".local/share/Trash/files/old.log").read_text() == "x"


def test_out_of_range_rows_are_refused_rather_than_crashing(tmp_path):
    model = _model(tmp_path)
    assert not model.deleteRow(5) and not model.renameRow(-1, "x")
