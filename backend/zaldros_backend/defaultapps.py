"""Default applications and the installed application list.

There is no service to ask: the freedesktop answer is a text file, `mimeapps.list`, read from the
XDG config directories in order and written only in the user's own
`$XDG_CONFIG_HOME/mimeapps.list` [freedesktop.org "Association between MIME types and
applications" 1.0.1]. `xdg-mime` is a shell script over exactly this file, so Zaldros edits the
file directly and gains an atomic write and no dependency on the script being installed.

The handful of "roles" Windows' Приложения по умолчанию page shows (browser, mail, images, music,
video, documents) map onto MIME types here; that mapping is data, listed below, not logic.
"""

from __future__ import annotations

import os
from pathlib import Path

from .bus import Result
from .reading import Reading

DEFAULTS_SECTION = "[Default Applications]"
ADDED_SECTION = "[Added Associations]"

# The roles the Settings page offers, and the MIME type each one really writes.
ROLES: dict[str, tuple[str, tuple[str, ...]]] = {
    "browser": ("Браузер", ("x-scheme-handler/http", "x-scheme-handler/https", "text/html")),
    "mail": ("Почта", ("x-scheme-handler/mailto",)),
    "images": ("Просмотр фотографий", ("image/jpeg", "image/png", "image/gif")),
    "music": ("Музыкальный проигрыватель", ("audio/mpeg", "audio/flac", "audio/x-vorbis+ogg")),
    "video": ("Видеопроигрыватель", ("video/mp4", "video/x-matroska", "video/webm")),
    "documents": ("Документы", ("application/pdf",)),
    "files": ("Файловый менеджер", ("inode/directory",)),
}


def config_home(home: Path | None = None) -> Path:
    if home is not None:
        return Path(home) / ".config"
    base = os.environ.get("XDG_CONFIG_HOME") or ""
    return Path(base) if base else Path.home() / ".config"


def search_paths(home: Path | None = None) -> list[Path]:
    """Every mimeapps.list that counts, most specific first — the order the spec defines."""
    paths = [config_home(home) / "mimeapps.list"]
    dirs = os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share"
    for directory in dirs.split(":"):
        if directory:
            paths.append(Path(directory) / "applications" / "mimeapps.list")
    return paths


def _read_sections(path: Path) -> dict[str, dict[str, str]]:
    sections: dict[str, dict[str, str]] = {}
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return sections
    current = ""
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            current = line
            sections.setdefault(current, {})
        elif current and "=" in line and not line.startswith("#"):
            key, _, value = line.partition("=")
            sections[current][key.strip()] = value.strip()
    return sections


class DefaultAppsFacet:
    """Reads and writes mimeapps.list. `home` is honoured so tests never touch a real one."""

    def __init__(self, home: Path | None = None, name_lookup=None) -> None:
        self._home = home
        # desktop id -> human name. The shell passes its application index; without one the file
        # name is shown, which is honest and still recognisable ("firefox.desktop" -> "firefox").
        self._name_lookup = name_lookup

    # -- reading -----------------------------------------------------------------------------
    def handler(self, mime_type: str) -> str:
        for path in search_paths(self._home):
            sections = _read_sections(path)
            value = sections.get(DEFAULTS_SECTION, {}).get(mime_type, "")
            if value:
                return value.split(";")[0].strip()
        return ""

    def role(self, role: str) -> Reading:
        """What opens this kind of file, by the first MIME type of the role."""
        if role not in ROLES:
            return Reading.missing("нет такой роли", role)
        title, types = ROLES[role]
        desktop_id = self.handler(types[0])
        if not desktop_id:
            return Reading.missing("не задано", str(search_paths(self._home)[0]))
        return Reading.measured(None, self.display_name(desktop_id),
                                str(search_paths(self._home)[0]),
                                role=role, title=title, desktop_id=desktop_id,
                                mime_types=list(types))

    def roles(self) -> list[Reading]:
        return [self.role(role) for role in ROLES]

    def display_name(self, desktop_id: str) -> str:
        """The application's own Name=, when the shell gave us an index; the file name otherwise."""
        if self._name_lookup is not None:
            name = self._name_lookup(desktop_id)
            if name:
                return name
        return desktop_id[:-8] if desktop_id.endswith(".desktop") else desktop_id

    # -- writing -----------------------------------------------------------------------------
    def set_role(self, role: str, desktop_id: str) -> Result:
        if role not in ROLES:
            return Result.bad(f"unknown role {role!r}", "mimeapps.list")
        _title, types = ROLES[role]
        return self.set_handlers({mime: desktop_id for mime in types})

    def set_handlers(self, assignments: dict[str, str]) -> Result:
        """Write [Default Applications] entries, keeping every other line of the file.

        Written atomically through a temporary file: a half-written mimeapps.list would leave the
        desktop unable to open anything, and that is not an acceptable outcome of a click.
        """
        path = search_paths(self._home)[0]
        sections = _read_sections(path)
        sections.setdefault(DEFAULTS_SECTION, {})
        for mime, desktop_id in assignments.items():
            sections[DEFAULTS_SECTION][mime] = desktop_id
            sections.setdefault(ADDED_SECTION, {}).setdefault(mime, desktop_id)
        body = []
        for name in [DEFAULTS_SECTION, ADDED_SECTION] + [s for s in sections
                                                         if s not in (DEFAULTS_SECTION,
                                                                      ADDED_SECTION)]:
            if name not in sections:
                continue
            body.append(name)
            body.extend(f"{key}={value}" for key, value in sorted(sections[name].items()))
            body.append("")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(".list.tmp")
            temporary.write_text("\n".join(body), encoding="utf-8")
            os.replace(temporary, path)
        except OSError as exc:
            return Result.bad(str(exc), str(path))
        return Result.good(True, str(path))
