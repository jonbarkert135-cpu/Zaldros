"""Win+V: the clipboard history must be the real clipboard, with Windows' own rules.

The rules being enforced here are Windows 11's, not ours: 25 entries, a re-copy moves an entry to
the top instead of duplicating it, "Очистить все" spares the pinned entries, and pins survive a
reboot. The privacy rule is ours: only pinned entries are ever written to disk.
"""

import json
from pathlib import Path

import pytest

from zaldros_shell import clipboard

REPO = Path(__file__).resolve().parents[3]
QML = (REPO / "shell" / "zaldros-shell" / "qml" / "ClipboardFlyout.qml").read_text()
SHELL_QML = (REPO / "shell" / "zaldros-shell" / "qml" / "Shell.qml").read_text()


def test_a_copy_becomes_an_entry_and_empty_copies_do_not(tmp_path):
    history = clipboard.History(home=tmp_path)
    assert history.add_text("привет") is True
    assert history.add_text("   ") is False
    assert history.add_text("") is False
    assert len(history) == 1
    assert history[0].kind == "text" and history[0].text == "привет"


def test_copying_the_same_text_again_moves_it_up_instead_of_duplicating(tmp_path):
    history = clipboard.History(home=tmp_path)
    for text in ("один", "два", "три"):
        history.add_text(text)
    history.add_text("один")
    assert [entry.text for entry in history.entries] == ["один", "три", "два"]


def test_the_history_stops_at_twenty_five_and_drops_the_oldest_unpinned(tmp_path):
    history = clipboard.History(home=tmp_path)
    for number in range(clipboard.MAX_ENTRIES + 5):
        history.add_text(f"item {number}")
    assert len(history) == clipboard.MAX_ENTRIES
    assert history[0].text == f"item {clipboard.MAX_ENTRIES + 4}"
    assert "item 0" not in [entry.text for entry in history.entries]


def test_a_pinned_entry_is_never_pushed_out_by_new_copies(tmp_path):
    history = clipboard.History(home=tmp_path)
    history.add_text("важное")
    history.toggle_pin(0)
    for number in range(clipboard.MAX_ENTRIES + 10):
        history.add_text(f"noise {number}")
    assert "важное" in [entry.text for entry in history.entries]


def test_clear_all_keeps_exactly_the_pinned_entries(tmp_path):
    history = clipboard.History(home=tmp_path)
    history.add_text("a")
    history.add_text("b")
    history.toggle_pin(0)                      # "b" is on top
    assert history.clear() == 1
    assert [entry.text for entry in history.entries] == ["b"]


def test_only_pinned_entries_reach_the_disk(tmp_path):
    history = clipboard.History(home=tmp_path)
    history.add_text("пароль от почты")
    history.add_text("закреплённое")
    history.toggle_pin(0)
    saved = json.loads(clipboard.pinned_path(tmp_path).read_text(encoding="utf-8"))
    assert [item["text"] for item in saved] == ["закреплённое"]
    # a new session sees the pin and nothing else
    assert [entry.text for entry in clipboard.History(home=tmp_path).entries] == ["закреплённое"]
    assert "пароль от почты" not in clipboard.pinned_path(tmp_path).read_text(encoding="utf-8")


def test_the_preview_collapses_whitespace_and_elides(tmp_path):
    history = clipboard.History(home=tmp_path)
    history.add_text("строка\n\nвторая     строка")
    assert history[0].preview() == "строка вторая строка"
    history.add_text("x" * 500)
    assert len(history[0].preview()) == 220 and history[0].preview().endswith("…")


# --- the Qt side ---------------------------------------------------------------------------

@pytest.fixture
def qt_clipboard():
    from PySide6.QtGui import QGuiApplication
    import sys
    app = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])
    return app.clipboard()


def test_the_model_records_what_is_really_copied(tmp_path, qt_clipboard):
    from zaldros_shell.model import ClipboardModel
    model = ClipboardModel(home=tmp_path, cache=tmp_path / "cache")
    qt_clipboard.setText("скопировано в этом сеансе")
    assert model.rowCount() >= 1
    from PySide6.QtCore import Qt
    preview_role = [role for role, name in model.roleNames().items() if name == b"preview"][0]
    assert model.data(model.index(0, 0), preview_role) == "скопировано в этом сеансе"


def test_activating_a_row_puts_it_back_on_the_clipboard(tmp_path, qt_clipboard):
    from zaldros_shell.model import ClipboardModel
    model = ClipboardModel(home=tmp_path, cache=tmp_path / "cache")
    qt_clipboard.setText("первое")
    qt_clipboard.setText("второе")
    assert model.applyRow(1) is True
    assert qt_clipboard.text() == "первое"


def test_clear_all_from_qml_leaves_the_pinned_card(tmp_path, qt_clipboard):
    from zaldros_shell.model import ClipboardModel
    model = ClipboardModel(home=tmp_path, cache=tmp_path / "cache")
    qt_clipboard.setText("временное")
    qt_clipboard.setText("нужное")
    model.pinRow(0)
    before = model.rowCount()
    assert model.clearAll() == before - 1        # everything but the pinned card
    assert model.rowCount() == 1


# --- the flyout ----------------------------------------------------------------------------

def test_the_flyout_is_bound_to_the_real_model_and_not_to_sample_data():
    assert "flyout.clipboard.applyRow(index)" in QML
    assert "flyout.clipboard.clearAll()" in QML
    assert "flyout.clipboard.pinRow(index)" in QML
    assert "ListModel" not in QML                 # no hand-written fake rows


def test_win_v_opens_it_and_closes_the_other_flyouts():
    assert '"Meta+V"' in SHELL_QML
    assert "shell.clipboardOpen = false;" in SHELL_QML.split("function closeAllFlyouts")[1]


def test_the_panel_keeps_the_measured_windows_geometry():
    reference = json.loads((REPO / "system" / "theme" / "win11-reference.json").read_text())
    theme = (REPO / "shell" / "zaldros-shell" / "qml" / "ZaldrosTheme" / "Theme.qml").read_text()
    clip = reference["clipboard"]
    assert f"clipboardWidth:    {clip['width']}" in theme
    assert f"clipboardCardHeight: {clip['card_height']}" in theme
    assert f"clipboardCardGap:    {clip['card_gap']}" in theme
