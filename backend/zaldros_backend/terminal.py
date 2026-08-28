# SPDX-License-Identifier: GPL-3.0-or-later
"""A real terminal: a pty, a VT parser and a screen buffer.

Windows Terminal is a window around conpty. Zaldros Terminal is a window around a Unix pty, which
is the same arrangement with a better kernel underneath. This module is the part with no Qt in it:

* `PtySession` — forks a shell on a pty, reads and writes bytes, resizes with `TIOCSWINSZ` so
  `stty size` inside the shell is right and full-screen programs lay out correctly.
* `Screen` — the VT parser and the character grid. Enough of xterm's sequences for interactive
  shells: cursor movement, erase, SGR colours and attributes, scroll region, alternate screen,
  tabs, backspace, carriage return, and the OSC title. What is not implemented is *ignored
  silently and completely* (never printed as garbage), and the list of what is ignored is in the
  ADR rather than in a comment nobody reads.
* `profiles()` — the shells that really exist on this machine, from /etc/shells and PATH.

Deliberately not a dependency: pyte and vte both do this well, but pyte is a Python package we
would have to ship and vte is a GTK widget. A pty plus a parser is ~400 lines and no runtime
dependency on the ISO.
"""

from __future__ import annotations

import errno
import fcntl
import os
import pty
import re
import shutil
import signal
import struct
import termios
from dataclasses import dataclass, field

DEFAULT_COLUMNS, DEFAULT_ROWS = 120, 30

# The 16 ANSI colours, in the Windows Terminal "Campbell" scheme — Microsoft's own default, and
# published as part of the open-source Windows Terminal (MIT), so we may use the values.
CAMPBELL = ["#0c0c0c", "#c50f1f", "#13a10e", "#c19c00", "#0037da", "#881798", "#3a96dd",
            "#cccccc", "#767676", "#e74856", "#16c60c", "#f9f1a5", "#3b78ff", "#b4009e",
            "#61d6d6", "#f2f2f2"]
DEFAULT_FOREGROUND, DEFAULT_BACKGROUND = "#cccccc", "#0c0c0c"

# Shells worth offering, in the order Windows Terminal's dropdown would list them: the login
# shell first, then whatever else is installed. PowerShell is `pwsh` — the MIT-licensed
# cross-platform build, never a Windows binary.
KNOWN_SHELLS = (("bash", "Bash"), ("zsh", "Zsh"), ("fish", "Fish"),
                ("pwsh", "PowerShell"), ("sh", "sh"))


@dataclass(frozen=True)
class Profile:
    """One entry of the new-tab dropdown."""

    name: str
    command: str
    is_default: bool = False

    def as_row(self) -> dict:
        return {"name": self.name, "command": self.command, "default": self.is_default}


def profiles() -> list[Profile]:
    """Shells that exist on this machine. Nothing is offered that cannot be started."""
    login = os.environ.get("SHELL", "")
    found: list[Profile] = []
    seen: set[str] = set()
    if login and os.path.exists(login):
        found.append(Profile(_shell_title(login), login, True))
        seen.add(os.path.realpath(login))
    for command, title in KNOWN_SHELLS:
        path = shutil.which(command)
        if not path or os.path.realpath(path) in seen:
            continue
        seen.add(os.path.realpath(path))
        found.append(Profile(title, path, not found))
    return found


def _shell_title(path: str) -> str:
    name = os.path.basename(path)
    for command, title in KNOWN_SHELLS:
        if name == command:
            return title
    return name


@dataclass
class Cell:
    """One character on screen, with the attributes it was drawn with."""

    text: str = " "
    foreground: str = DEFAULT_FOREGROUND
    background: str = DEFAULT_BACKGROUND
    bold: bool = False
    underline: bool = False
    inverse: bool = False


@dataclass
class Attributes:
    foreground: str = DEFAULT_FOREGROUND
    background: str = DEFAULT_BACKGROUND
    bold: bool = False
    underline: bool = False
    inverse: bool = False

    def copy(self) -> "Attributes":
        return Attributes(self.foreground, self.background, self.bold, self.underline,
                          self.inverse)


def _decode_partial(chunk: bytes) -> tuple[str, bytes]:
    """Decode as much valid UTF-8 as possible; return the undecodable tail separately."""
    try:
        return (chunk.decode("utf-8"), b"")
    except UnicodeDecodeError as error:
        if error.end == len(chunk):                  # truncated sequence at the end: keep it
            return (chunk[:error.start].decode("utf-8"), chunk[error.start:])
        return (chunk.decode("utf-8", errors="replace"), b"")


CSI = re.compile(rb"\x1b\[([0-?]*)([ -/]*)([@-~])")
OSC = re.compile(rb"\x1b\]([^\x07\x1b]*)(?:\x07|\x1b\\)")


class Screen:
    """The character grid, and the parser that fills it.

    Scrollback is kept because a terminal without it is a toy; it is capped, and the cap is a
    number here rather than "until the machine dies".
    """

    def __init__(self, columns: int = DEFAULT_COLUMNS, rows: int = DEFAULT_ROWS,
                 scrollback: int = 2000) -> None:
        self.columns = max(1, columns)
        self.rows = max(1, rows)
        self.scrollback_limit = scrollback
        self.title = ""
        self._reset()

    def _reset(self) -> None:
        self.grid = [[Cell() for _ in range(self.columns)] for _ in range(self.rows)]
        self.scrollback: list[list[Cell]] = []
        self.cursor_x = 0
        self.cursor_y = 0
        self.attributes = Attributes()
        self.saved_cursor = (0, 0)
        self.scroll_top, self.scroll_bottom = 0, self.rows - 1
        self.alternate: list[list[Cell]] | None = None
        self._pending = b""

    # -- geometry -------------------------------------------------------------------------
    def resize(self, columns: int, rows: int) -> None:
        columns, rows = max(1, columns), max(1, rows)
        for line in self.grid:
            if len(line) < columns:
                line.extend(Cell() for _ in range(columns - len(line)))
            del line[columns:]
        while len(self.grid) < rows:
            self.grid.append([Cell() for _ in range(columns)])
        while len(self.grid) > rows:
            # Rows disappearing off the top go to scrollback, not to nothing: a resize must never
            # eat output the user has not read.
            self.scrollback.append(self.grid.pop(0))
        self.columns, self.rows = columns, rows
        self.scroll_top = min(self.scroll_top, rows - 1)
        self.scroll_bottom = rows - 1
        self.cursor_x = min(self.cursor_x, columns - 1)
        self.cursor_y = min(self.cursor_y, rows - 1)
        self._trim()

    def _trim(self) -> None:
        excess = len(self.scrollback) - self.scrollback_limit
        if excess > 0:
            del self.scrollback[:excess]

    # -- text output ----------------------------------------------------------------------
    def feed(self, data: bytes) -> None:
        """Parse a chunk. A sequence split across two reads is held over, not mangled."""
        data = self._pending + data
        self._pending = b""
        index = 0
        while index < len(data):
            byte = data[index:index + 1]
            if byte == b"\x1b":
                consumed = self._escape(data, index)
                if consumed == 0:                 # incomplete: wait for the rest
                    self._pending = data[index:]
                    return
                index += consumed
                continue
            if byte in (b"\r", b"\n", b"\b", b"\t", b"\x07"):
                self._control(byte)
                index += 1
                continue
            if byte < b" ":
                index += 1                        # unsupported control: dropped, never printed
                continue
            end = index
            while end < len(data) and data[end:end + 1] >= b" " and data[end:end + 1] != b"\x1b":
                end += 1
            chunk = data[index:end]
            # A multi-byte character can be split across two reads from the pty. Decoding each
            # chunk independently would turn «привет» into replacement characters, so the tail of
            # an incomplete sequence is held over to the next feed().
            text, kept = _decode_partial(chunk)
            if kept and end >= len(data):
                self._pending = kept
            elif kept:
                text += kept.decode("utf-8", errors="replace")
            self._write(text)
            index = end

    def _control(self, byte: bytes) -> None:
        if byte == b"\r":
            self.cursor_x = 0
        elif byte == b"\n":
            self._newline()
        elif byte == b"\b":
            self.cursor_x = max(0, self.cursor_x - 1)
        elif byte == b"\t":
            self.cursor_x = min(self.columns - 1, (self.cursor_x // 8 + 1) * 8)
        # \x07 is the bell: a terminal that beeps in a container is worse than one that does not.

    def _write(self, text: str) -> None:
        for character in text:
            if self.cursor_x >= self.columns:
                self.cursor_x = 0
                self._newline()
            self.grid[self.cursor_y][self.cursor_x] = Cell(
                character, self.attributes.foreground, self.attributes.background,
                self.attributes.bold, self.attributes.underline, self.attributes.inverse)
            self.cursor_x += 1

    def _newline(self) -> None:
        if self.cursor_y == self.scroll_bottom:
            line = self.grid.pop(self.scroll_top)
            if self.scroll_top == 0 and self.alternate is None:
                self.scrollback.append(line)
                self._trim()
            self.grid.insert(self.scroll_bottom, [Cell() for _ in range(self.columns)])
        else:
            self.cursor_y = min(self.cursor_y + 1, self.rows - 1)

    # -- escape sequences -----------------------------------------------------------------
    def _escape(self, data: bytes, index: int) -> int:
        rest = data[index:]
        if len(rest) < 2:
            return 0
        match = CSI.match(rest)
        if match:
            self._csi(match.group(1), match.group(2), match.group(3))
            return match.end()
        match = OSC.match(rest)
        if match:
            payload = match.group(1).decode("utf-8", errors="replace")
            code, _, value = payload.partition(";")
            if code in ("0", "2"):
                self.title = value            # the tab title the shell sets, as Windows shows it
            return match.end()
        second = rest[1:2]
        if second in (b"[", b"]"):
            return 0                          # incomplete CSI/OSC: wait for more bytes
        if second == b"7":
            self.saved_cursor = (self.cursor_x, self.cursor_y)
        elif second == b"8":
            self.cursor_x, self.cursor_y = self.saved_cursor
        elif second == b"M":
            self.cursor_y = max(0, self.cursor_y - 1)
        elif second == b"c":
            self._reset()
        return 2

    def _csi(self, parameters: bytes, intermediate: bytes, final: bytes) -> None:
        private = parameters.startswith(b"?")
        text = parameters[1:] if private else parameters
        values = [int(part) if part.isdigit() else 0
                  for part in text.decode("ascii", "replace").split(";")] or [0]
        command = final.decode("ascii", "replace")
        first = values[0]

        if private:
            self._private_mode(values, command)
            return
        if command == "A":
            self.cursor_y = max(0, self.cursor_y - max(1, first))
        elif command == "B":
            self.cursor_y = min(self.rows - 1, self.cursor_y + max(1, first))
        elif command == "C":
            self.cursor_x = min(self.columns - 1, self.cursor_x + max(1, first))
        elif command == "D":
            self.cursor_x = max(0, self.cursor_x - max(1, first))
        elif command in ("H", "f"):
            row = (values[0] or 1) - 1
            column = (values[1] - 1) if len(values) > 1 and values[1] else 0
            self.cursor_y = max(0, min(self.rows - 1, row))
            self.cursor_x = max(0, min(self.columns - 1, column))
        elif command == "G":
            self.cursor_x = max(0, min(self.columns - 1, (first or 1) - 1))
        elif command == "d":
            self.cursor_y = max(0, min(self.rows - 1, (first or 1) - 1))
        elif command == "J":
            self._erase_display(first)
        elif command == "K":
            self._erase_line(first)
        elif command == "L":
            for _ in range(max(1, first)):
                self.grid.insert(self.cursor_y, [Cell() for _ in range(self.columns)])
                del self.grid[self.scroll_bottom + 1:self.scroll_bottom + 2]
        elif command == "M":
            for _ in range(max(1, first)):
                del self.grid[self.cursor_y]
                self.grid.insert(self.scroll_bottom, [Cell() for _ in range(self.columns)])
        elif command == "P":
            line = self.grid[self.cursor_y]
            del line[self.cursor_x:self.cursor_x + max(1, first)]
            line.extend(Cell() for _ in range(self.columns - len(line)))
        elif command == "X":
            for offset in range(max(1, first)):
                if self.cursor_x + offset < self.columns:
                    self.grid[self.cursor_y][self.cursor_x + offset] = Cell()
        elif command == "m":
            self._sgr(values)
        elif command == "r":
            top = (values[0] or 1) - 1
            bottom = (values[1] - 1) if len(values) > 1 and values[1] else self.rows - 1
            self.scroll_top = max(0, min(top, self.rows - 1))
            self.scroll_bottom = max(self.scroll_top, min(bottom, self.rows - 1))
            self.cursor_x, self.cursor_y = 0, self.scroll_top
        elif command == "s":
            self.saved_cursor = (self.cursor_x, self.cursor_y)
        elif command == "u":
            self.cursor_x, self.cursor_y = self.saved_cursor
        # Everything else is ignored on purpose; see ADR-0019 for the list.

    def _private_mode(self, values: list[int], command: str) -> None:
        if command not in ("h", "l"):
            return
        enabled = command == "h"
        for value in values:
            if value in (1049, 47, 1047):
                self._alternate_screen(enabled)

    def _alternate_screen(self, enabled: bool) -> None:
        """vim and less live here. Their output must not land in the scrollback of the shell."""
        if enabled and self.alternate is None:
            self.alternate = self.grid
            self.grid = [[Cell() for _ in range(self.columns)] for _ in range(self.rows)]
            self.saved_cursor = (self.cursor_x, self.cursor_y)
            self.cursor_x = self.cursor_y = 0
        elif not enabled and self.alternate is not None:
            self.grid = self.alternate
            self.alternate = None
            self.cursor_x, self.cursor_y = self.saved_cursor

    def _erase_display(self, mode: int) -> None:
        if mode == 2 or mode == 3:
            self.grid = [[Cell() for _ in range(self.columns)] for _ in range(self.rows)]
            if mode == 3:
                self.scrollback.clear()
            return
        if mode == 0:
            self._erase_line(0)
            for row in range(self.cursor_y + 1, self.rows):
                self.grid[row] = [Cell() for _ in range(self.columns)]
        elif mode == 1:
            self._erase_line(1)
            for row in range(0, self.cursor_y):
                self.grid[row] = [Cell() for _ in range(self.columns)]

    def _erase_line(self, mode: int) -> None:
        line = self.grid[self.cursor_y]
        span = range(self.cursor_x, self.columns) if mode == 0 else \
            range(0, self.cursor_x + 1) if mode == 1 else range(0, self.columns)
        for column in span:
            line[column] = Cell()

    def _sgr(self, values: list[int]) -> None:
        index = 0
        while index < len(values):
            value = values[index]
            if value == 0:
                self.attributes = Attributes()
            elif value == 1:
                self.attributes.bold = True
            elif value == 4:
                self.attributes.underline = True
            elif value == 7:
                self.attributes.inverse = True
            elif value == 22:
                self.attributes.bold = False
            elif value == 24:
                self.attributes.underline = False
            elif value == 27:
                self.attributes.inverse = False
            elif 30 <= value <= 37:
                self.attributes.foreground = CAMPBELL[value - 30]
            elif 90 <= value <= 97:
                self.attributes.foreground = CAMPBELL[value - 90 + 8]
            elif 40 <= value <= 47:
                self.attributes.background = CAMPBELL[value - 40]
            elif 100 <= value <= 107:
                self.attributes.background = CAMPBELL[value - 100 + 8]
            elif value == 39:
                self.attributes.foreground = DEFAULT_FOREGROUND
            elif value == 49:
                self.attributes.background = DEFAULT_BACKGROUND
            elif value in (38, 48) and index + 1 < len(values):
                colour, consumed = self._extended_colour(values, index)
                if colour:
                    if value == 38:
                        self.attributes.foreground = colour
                    else:
                        self.attributes.background = colour
                index += consumed
            index += 1

    def _extended_colour(self, values: list[int], index: int) -> tuple[str, int]:
        mode = values[index + 1]
        if mode == 5 and index + 2 < len(values):
            return (_xterm256(values[index + 2]), 2)
        if mode == 2 and index + 4 < len(values):
            red, green, blue = values[index + 2:index + 5]
            return (f"#{red:02x}{green:02x}{blue:02x}", 4)
        return ("", 1)

    # -- what the UI reads -----------------------------------------------------------------
    def lines(self, include_scrollback: int = 0) -> list[list[dict]]:
        """Rows of runs: consecutive cells with the same attributes are merged, because a QML
        Text per character at 120x30 is 3600 items and a stutter."""
        source = (self.scrollback[-include_scrollback:] if include_scrollback else []) + self.grid
        out: list[list[dict]] = []
        for line in source:
            runs: list[dict] = []
            for cell in line:
                style = (cell.foreground, cell.background, cell.bold, cell.underline, cell.inverse)
                if runs and runs[-1]["_style"] == style:
                    runs[-1]["text"] += cell.text
                    continue
                runs.append({"text": cell.text, "foreground": cell.foreground,
                             "background": cell.background, "bold": cell.bold,
                             "underline": cell.underline, "inverse": cell.inverse,
                             "_style": style})
            for run in runs:
                run.pop("_style")
            out.append(runs)
        return out

    def text(self) -> str:
        """The visible screen as plain text — what «Копировать» puts on the clipboard."""
        return "\n".join("".join(cell.text for cell in line).rstrip() for line in self.grid)


def _xterm256(value: int) -> str:
    if value < 16:
        return CAMPBELL[value]
    if value < 232:
        value -= 16
        levels = (0, 95, 135, 175, 215, 255)
        return "#%02x%02x%02x" % (levels[value // 36], levels[value // 6 % 6], levels[value % 6])
    grey = 8 + (value - 232) * 10
    return f"#{grey:02x}{grey:02x}{grey:02x}"


class PtySession:
    """A shell on a pty. The only thing here that touches the operating system."""

    def __init__(self, command: str = "", columns: int = DEFAULT_COLUMNS,
                 rows: int = DEFAULT_ROWS, cwd: str = "") -> None:
        self.command = command or os.environ.get("SHELL") or "/bin/sh"
        self.screen = Screen(columns, rows)
        self.pid = -1
        self.fd = -1
        self.exit_status: int | None = None
        self._cwd = cwd or os.path.expanduser("~")

    def start(self) -> bool:
        if self.pid > 0:
            return True
        if not os.path.exists(self.command):
            return False
        pid, fd = pty.fork()
        if pid == 0:                                   # child: becomes the shell
            try:
                os.chdir(self._cwd)
            except OSError:
                pass
            # TERM matters: without it ncurses programs refuse to run, and `xterm-256color` is
            # what our parser actually implements.
            os.environ["TERM"] = "xterm-256color"
            os.environ["COLORTERM"] = "truecolor"
            try:
                os.execv(self.command, [self.command])
            except OSError:
                os._exit(127)
        self.pid, self.fd = pid, fd
        os.set_blocking(fd, False)
        self.resize(self.screen.columns, self.screen.rows)
        return True

    def resize(self, columns: int, rows: int) -> None:
        self.screen.resize(columns, rows)
        if self.fd >= 0:
            try:
                fcntl.ioctl(self.fd, termios.TIOCSWINSZ,
                            struct.pack("HHHH", rows, columns, 0, 0))
            except OSError:
                pass

    def read(self, limit: int = 65536) -> bytes:
        """Whatever is waiting. Empty when nothing is, b"" and `alive=False` when the shell left."""
        if self.fd < 0:
            return b""
        try:
            data = os.read(self.fd, limit)
        except BlockingIOError:
            return b""
        except OSError as error:
            if error.errno in (errno.EIO, errno.EBADF):
                self._reap()
                return b""
            raise
        if not data:
            self._reap()
        else:
            self.screen.feed(data)
        return data

    def write(self, data: str | bytes) -> int:
        if self.fd < 0:
            return 0
        payload = data.encode("utf-8") if isinstance(data, str) else data
        try:
            return os.write(self.fd, payload)
        except OSError:
            return 0

    @property
    def alive(self) -> bool:
        if self.pid <= 0:
            return False
        try:
            pid, status = os.waitpid(self.pid, os.WNOHANG)
        except ChildProcessError:
            return False
        if pid == self.pid:
            self.exit_status = os.waitstatus_to_exitcode(status)
            return False
        return True

    def close(self) -> None:
        if self.fd >= 0:
            try:
                os.close(self.fd)
            except OSError:
                pass
            self.fd = -1
        if self.pid > 0:
            try:
                os.kill(self.pid, signal.SIGHUP)
                os.waitpid(self.pid, 0)
            except OSError:
                pass
            self.pid = -1

    def _reap(self) -> None:
        if self.fd >= 0:
            try:
                os.close(self.fd)
            except OSError:
                pass
            self.fd = -1
        if self.pid > 0:
            try:
                _pid, status = os.waitpid(self.pid, 0)
                self.exit_status = os.waitstatus_to_exitcode(status)
            except OSError:
                pass
            self.pid = -1


@dataclass
class Pane:
    """One pty inside a tab. Windows Terminal calls a split a pane; so do we."""

    session: PtySession
    title: str = ""


@dataclass
class Tab:
    """A tab holds one or more panes, split vertically (side by side) like Alt+Shift+Plus."""

    panes: list[Pane] = field(default_factory=list)
    active: int = 0
    name: str = ""
