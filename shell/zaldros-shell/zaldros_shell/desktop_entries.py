"""Real XDG .desktop application discovery and launching.

This replaces the placeholder pinned list. Everything here reads the actual application database of
the running system (`/usr/share/applications`, `~/.local/share/applications`, …) as specified by the
XDG Desktop Entry Specification, so what the Start menu shows is what the machine really has.
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
from configparser import ConfigParser, MissingSectionHeaderError, ParsingError
from dataclasses import dataclass
from pathlib import Path

FIELD_CODES = re.compile(r"%[fFuUdDnNickvm]")


@dataclass(frozen=True)
class DesktopApp:
    name: str
    exec_command: str
    icon: str
    categories: tuple[str, ...]
    comment: str = ""
    no_display: bool = False
    terminal: bool = False
    desktop_id: str = ""      # "firefox.desktop" — how mimeapps.list names this application

    @property
    def exec_name(self) -> str:
        """First token of Exec, used to match against /proc comm."""
        parts = shlex.split(self.exec_command) if self.exec_command else []
        return os.path.basename(parts[0]) if parts else ""

    @property
    def initial(self) -> str:
        return self.name[:1].upper() if self.name else "?"

    @property
    def sort_key(self) -> str:
        return self.name.casefold()


def application_dirs(env: dict[str, str] | None = None) -> list[Path]:
    env = env if env is not None else dict(os.environ)
    home = env.get("XDG_DATA_HOME") or os.path.join(env.get("HOME", "/root"), ".local/share")
    system = env.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share"
    roots = [home, *system.split(":")]
    return [Path(root) / "applications" for root in roots if root]


def parse_desktop_file(text: str, locale: str = "ru", desktop_id: str = "") -> DesktopApp | None:
    """Parse one .desktop file. Only the [Desktop Entry] group; localized Name[xx] wins."""
    # ponytail: configparser is the stdlib INI parser and .desktop is INI; strict=False tolerates
    # the duplicate keys real-world files ship. Swap for a hand parser only if a real file breaks it.
    parser = ConfigParser(interpolation=None, strict=False)
    parser.optionxform = str
    try:
        parser.read_string(text)
        values = dict(parser["Desktop Entry"])
    except (MissingSectionHeaderError, ParsingError, KeyError):
        return None

    if values.get("Type", "Application") != "Application":
        return None
    name = (values.get(f"Name[{locale}]") or values.get(f"Name[{locale.split('_')[0]}]")
            or values.get("Name"))
    if not name:
        return None
    return DesktopApp(
        name=name,
        exec_command=FIELD_CODES.sub("", values.get("Exec", "")).strip(),
        icon=values.get("Icon", ""),
        categories=tuple(c for c in values.get("Categories", "").split(";") if c),
        comment=values.get(f"Comment[{locale}]") or values.get("Comment", ""),
        no_display=values.get("NoDisplay", "false").lower() == "true"
                   or values.get("Hidden", "false").lower() == "true",
        terminal=values.get("Terminal", "false").lower() == "true",
        desktop_id=desktop_id,
    )


def discover(dirs: list[Path] | None = None, locale: str = "ru") -> list[DesktopApp]:
    """All visible applications on this system, de-duplicated by name, sorted like Windows does."""
    found: dict[str, DesktopApp] = {}
    for directory in (dirs if dirs is not None else application_dirs()):
        try:
            entries = sorted(directory.glob("*.desktop"))
        except OSError:
            continue
        for path in entries:
            try:
                app = parse_desktop_file(path.read_text(encoding="utf-8", errors="replace"),
                                         locale, path.name)
            except OSError:
                continue
            if app and not app.no_display and app.exec_command:
                found.setdefault(app.name, app)
    return sorted(found.values(), key=lambda a: a.sort_key)


def launch(app: DesktopApp, runner=subprocess.Popen) -> bool:
    """Start an application detached from the shell. Returns False if it could not be started."""
    if not app.exec_command:
        return False
    try:
        runner(shlex.split(app.exec_command), start_new_session=True,
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (OSError, ValueError):
        return False
    return True
