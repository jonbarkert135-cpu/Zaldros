"""Real file-system access for the Zaldros file manager.

The Explorer window shows the machine's actual files. Nothing here invents entries: an unreadable
directory reports the error, an empty directory reports that it is empty.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path

KIND_BY_SUFFIX = {
    ".txt": ("Текстовый документ", "document"),
    ".md": ("Документ Markdown", "document"),
    ".pdf": ("Документ PDF", "document"),
    ".png": ("Изображение PNG", "image"),
    ".jpg": ("Изображение JPEG", "image"),
    ".jpeg": ("Изображение JPEG", "image"),
    ".svg": ("Изображение SVG", "image"),
    ".mp3": ("Звуковой файл", "music"),
    ".flac": ("Звуковой файл", "music"),
    ".mp4": ("Видеофайл", "video"),
    ".mkv": ("Видеофайл", "video"),
    ".py": ("Файл Python", "document"),
    ".sh": ("Сценарий оболочки", "document"),
    ".json": ("Файл JSON", "document"),
    ".conf": ("Файл конфигурации", "document"),
    ".log": ("Файл журнала", "document"),
}


@dataclass(frozen=True)
class Entry:
    name: str
    path: str
    is_dir: bool
    size: int
    modified: float
    kind: str
    glyph: str


def human_size(size: int, is_dir: bool) -> str:
    if is_dir:
        return ""
    for unit, limit in (("КБ", 1024 ** 2), ("МБ", 1024 ** 3), ("ГБ", 1024 ** 4)):
        if size < limit:
            return f"{size / (limit // 1024):,.0f} {unit}".replace(",", " ")
    return f"{size / 1024 ** 4:,.1f} ТБ"


def format_modified(stamp: float) -> str:
    return time.strftime("%d.%m.%Y %H:%M", time.localtime(stamp))


def classify(path: Path, is_dir: bool) -> tuple[str, str]:
    if is_dir:
        return "Папка с файлами", "folder"
    return KIND_BY_SUFFIX.get(path.suffix.lower(), ("Файл", "document"))


def list_directory(directory: str | os.PathLike[str], show_hidden: bool = False) -> list[Entry]:
    """Directory contents, folders first then files, both alphabetical (Windows Explorer order)."""
    base = Path(directory)
    entries: list[Entry] = []
    for item in base.iterdir():
        if not show_hidden and item.name.startswith("."):
            continue
        try:
            stat = item.stat()
            is_dir = item.is_dir()
        except OSError:
            continue
        kind, glyph = classify(item, is_dir)
        entries.append(Entry(item.name, str(item), is_dir, 0 if is_dir else stat.st_size,
                             stat.st_mtime, kind, glyph))
    entries.sort(key=lambda entry: (not entry.is_dir, entry.name.casefold()))
    return entries


def quick_access(home: str | os.PathLike[str] | None = None) -> list[tuple[str, str, str]]:
    """Sidebar shortcuts that really exist on this machine: (label, path, freedesktop icon)."""
    root = Path(home) if home else Path.home()
    candidates = [
        ("Рабочий стол", root / "Desktop", "user-desktop"),
        ("Загрузки", root / "Downloads", "folder-download"),
        ("Документы", root / "Documents", "folder-documents"),
        ("Изображения", root / "Pictures", "folder-pictures"),
        ("Музыка", root / "Music", "folder-music"),
        ("Видео", root / "Videos", "folder-videos"),
    ]
    shortcuts = [("Главная", str(root), "user-home")]
    shortcuts += [(label, str(path), icon) for label, path, icon in candidates if path.is_dir()]
    return shortcuts


def recent_files(home: str | os.PathLike[str] | None = None, limit: int = 6,
                 depth: int = 2) -> list[Entry]:
    """The most recently modified regular files under the home directory.

    This is what the Start panel's "Рекомендуем" section shows. When nothing is found the caller
    shows an empty state instead of inventing recommendations.
    """
    root = Path(home) if home else Path.home()
    found: list[Entry] = []
    for path in _walk(root, depth):
        try:
            stat = path.stat()
        except OSError:
            continue
        kind, glyph = classify(path, False)
        found.append(Entry(path.name, str(path), False, stat.st_size, stat.st_mtime, kind, glyph))
    found.sort(key=lambda entry: entry.modified, reverse=True)
    return found[:limit]


def _walk(root: Path, depth: int):
    if depth < 0 or not root.is_dir():
        return
    try:
        items = list(root.iterdir())
    except OSError:
        return
    for item in items:
        if item.name.startswith("."):
            continue
        if item.is_file():
            yield item
        elif item.is_dir():
            yield from _walk(item, depth - 1)
