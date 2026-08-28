# SPDX-License-Identifier: GPL-3.0-or-later
"""Zaldros Terminal: the VT parser against known sequences, and a real shell on a real pty.

The parser tests are exact — a colour is a hex value from the Campbell palette, an erase leaves
spaces, an alternate screen does not pollute the scrollback. The pty tests run `bash` and read
back what it printed, because a terminal that passes parser tests and cannot run a shell is not a
terminal.
"""

from __future__ import annotations

import os
import time

import pytest

from zaldros_backend import terminal


def screen(*chunks: bytes, columns: int = 20, rows: int = 5) -> terminal.Screen:
    display = terminal.Screen(columns, rows)
    for chunk in chunks:
        display.feed(chunk)
    return display


def line(display: terminal.Screen, row: int) -> str:
    return "".join(cell.text for cell in display.grid[row]).rstrip()


# --- text and control characters ---------------------------------------------------------------
def test_plain_text_lands_on_the_first_line():
    assert line(screen(b"hello"), 0) == "hello"


def test_utf8_survives_being_split_across_two_reads():
    display = terminal.Screen(20, 3)
    data = "привет".encode("utf-8")
    display.feed(data[:5])
    display.feed(data[5:])
    assert line(display, 0) == "привет"


def test_carriage_return_and_newline_do_different_things():
    """CR returns to column 0; LF only moves down — the column is kept, as a real tty does.
    That is why shells send CRLF, and why a terminal that folds LF into CRLF misdraws `less`."""
    assert line(screen(b"abc\rX"), 0) == "Xbc"
    display = screen(b"a\nb")
    assert line(display, 1) == " b"


def test_backspace_moves_the_cursor_and_does_not_erase_by_itself():
    display = screen(b"abc\b")
    assert display.cursor_x == 2 and line(display, 0) == "abc"


def test_a_line_longer_than_the_screen_wraps_instead_of_being_cut():
    display = screen(b"x" * 25, columns=20)
    assert line(display, 0) == "x" * 20 and line(display, 1) == "x" * 5


# --- colours -------------------------------------------------------------------------------------
def test_sgr_sets_the_campbell_red_and_reset_puts_the_default_back():
    display = screen(b"\x1b[31mRED\x1b[0mplain")
    assert display.grid[0][0].foreground == terminal.CAMPBELL[1]
    assert display.grid[0][3].foreground == terminal.DEFAULT_FOREGROUND


def test_bright_colours_use_the_upper_half_of_the_palette():
    display = screen(b"\x1b[92mgreen")
    assert display.grid[0][0].foreground == terminal.CAMPBELL[10]


def test_a_256_colour_and_a_truecolour_sequence_both_resolve():
    assert screen(b"\x1b[38;5;196mx").grid[0][0].foreground == "#ff0000"
    assert screen(b"\x1b[38;2;18;52;86mx").grid[0][0].foreground == "#123456"


def test_bold_and_underline_are_attributes_not_characters():
    cell = screen(b"\x1b[1;4mx").grid[0][0]
    assert cell.bold and cell.underline and cell.text == "x"


# --- cursor and erase ------------------------------------------------------------------------------
def test_cursor_addressing_is_one_based_on_the_wire_and_zero_based_inside():
    display = screen(b"\x1b[3;5H")
    assert (display.cursor_y, display.cursor_x) == (2, 4)


def test_erase_display_clears_the_screen_but_keeps_the_scrollback():
    display = screen(b"one\ntwo\n" * 4, columns=20, rows=3)
    before = len(display.scrollback)
    display.feed(b"\x1b[2J")
    assert line(display, 0) == "" and len(display.scrollback) == before


def test_erase_to_end_of_line_leaves_what_is_before_the_cursor():
    display = screen(b"abcdef\x1b[1;4H\x1b[K")
    assert line(display, 0) == "abc"


def test_delete_characters_pulls_the_rest_of_the_line_left():
    display = screen(b"abcdef\x1b[1;2H\x1b[2P")
    assert line(display, 0) == "adef"


# --- the alternate screen -------------------------------------------------------------------------
def test_vim_does_not_leave_its_screen_in_the_scrollback():
    display = screen(b"prompt\n", columns=20, rows=3)
    display.feed(b"\x1b[?1049h")
    display.feed(b"file contents\n" * 6)
    length = len(display.scrollback)
    display.feed(b"\x1b[?1049l")
    assert len(display.scrollback) == length          # nothing from the alternate screen leaked
    assert "prompt" in line(display, 0)


# --- geometry ---------------------------------------------------------------------------------------
def test_shrinking_the_window_pushes_rows_into_the_scrollback_instead_of_dropping_them():
    display = screen(b"1\n2\n3\n4\n5", columns=10, rows=5)
    display.resize(10, 2)
    assert display.rows == 2
    assert any("1" in "".join(cell.text for cell in row) for row in display.scrollback)


def test_the_scrollback_is_capped():
    display = terminal.Screen(10, 2, scrollback=5)
    display.feed(b"x\n" * 50)
    assert len(display.scrollback) == 5


# --- titles and unknown sequences ------------------------------------------------------------------
def test_the_shell_can_set_the_tab_title():
    assert screen(b"\x1b]0;~/projects\x07").title == "~/projects"


def test_an_unimplemented_sequence_is_swallowed_and_never_printed_as_garbage():
    display = screen(b"a\x1b[>4;2mb")
    assert line(display, 0) == "ab"


# --- a real shell on a real pty -----------------------------------------------------------------------
def wait_for(session: terminal.PtySession, text: str, timeout: float = 8.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        session.read()
        if text in session.screen.text():
            return True
        time.sleep(0.05)
    return False


@pytest.fixture()
def shell():
    profiles = terminal.profiles()
    if not profiles:
        pytest.skip("no shell on this machine")
    session = terminal.PtySession(profiles[0].command, 80, 24)
    assert session.start()
    yield session
    session.close()


def test_a_real_shell_starts_and_answers(shell):
    shell.write("echo zaldros-terminal-ok\n")
    assert wait_for(shell, "zaldros-terminal-ok")


def test_the_shell_sees_the_size_we_gave_the_pty(shell):
    shell.write("stty size\n")
    assert wait_for(shell, "24 80")


def test_resizing_reaches_the_shell_not_just_our_own_grid(shell):
    shell.resize(100, 30)
    shell.write("stty size\n")
    assert wait_for(shell, "30 100")


def test_colour_from_a_real_program_is_parsed_into_attributes(shell):
    # The echo of the typed command contains the word too, so waiting for the *text* would pass
    # before printf ever ran: wait for a run that is actually green.
    shell.write("printf '\\033[32mGREENTEXT\\033[0m\\n'\n")
    deadline = time.monotonic() + 8
    coloured: list = []
    while time.monotonic() < deadline and not coloured:
        shell.read()
        coloured = [run for row in shell.screen.lines() for run in row
                    if run["text"].strip() == "GREENTEXT"
                    and run["foreground"] == terminal.CAMPBELL[2]]
        time.sleep(0.05)
    assert coloured


def test_a_shell_that_exits_is_reported_dead_with_its_exit_code(shell):
    shell.write("exit 3\n")
    deadline = time.monotonic() + 8
    while shell.alive and time.monotonic() < deadline:
        shell.read()
        time.sleep(0.05)
    assert not shell.alive and shell.exit_status == 3


def test_a_profile_is_only_offered_when_the_shell_really_exists():
    for profile in terminal.profiles():
        assert os.path.exists(profile.command)


def test_a_session_for_a_shell_that_is_not_installed_refuses_to_start():
    session = terminal.PtySession("/usr/bin/definitely-not-a-shell")
    assert not session.start() and session.pid == -1
