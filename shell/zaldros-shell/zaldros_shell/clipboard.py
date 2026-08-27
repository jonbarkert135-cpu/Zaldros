"""Clipboard history — the data behind Win+V.

No Qt in here: the history is a plain structure so it can be tested without a display, exactly
like files.py and prefs.py. `model.ClipboardModel` connects it to the real QClipboard.

What Windows 11 does, and what this follows:

* the flyout keeps the **last 25 entries**; the 26th pushes the oldest unpinned one out;
* copying something that is already in the list **moves it to the top** instead of duplicating it;
* **pinned** entries survive both "Очистить все" and a reboot — they are the only part written to
  disk (`$XDG_CONFIG_HOME/zaldros/clipboard-pinned.json`), because an unpinned history that
  outlives the session is a privacy leak, not a feature;
* "Очистить все" removes everything **except** the pinned entries.

Images are kept as a file path, never as a copy of the bytes in this list; the model writes the
bitmap into a cache directory and stores the path, so the history stays small.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

MAX_ENTRIES = 25            # Windows 11 keeps 25; the 26th copy drops the oldest unpinned one


@dataclass
class Entry:
    """One clipboard item. `text` is the whole payload for text; `path` for an image."""

    kind: str                       # "text" | "image"
    text: str = ""
    path: str = ""
    pinned: bool = False
    when: float = field(default_factory=time.time)

    @property
    def key(self) -> str:
        return self.text if self.kind == "text" else self.path

    def preview(self, limit: int = 220) -> str:
        """What the card shows. Whitespace is collapsed the way the Windows card does it."""
        if self.kind != "text":
            return Path(self.path).name
        flat = " ".join(self.text.split())
        return flat if len(flat) <= limit else flat[: limit - 1] + "…"


def pinned_path(home: Path | None = None) -> Path:
    if home is not None:
        return Path(home) / ".config" / "zaldros" / "clipboard-pinned.json"
    base = os.environ.get("XDG_CONFIG_HOME") or ""
    root = Path(base) if base else Path.home() / ".config"
    return root / "zaldros" / "clipboard-pinned.json"


class History:
    """The clipboard history. Ordered newest first."""

    def __init__(self, home: Path | None = None, limit: int = MAX_ENTRIES) -> None:
        self._home = home
        self._limit = limit
        self.entries: list[Entry] = self._load_pinned()

    # --- reading -------------------------------------------------------------------------
    def __len__(self) -> int:
        return len(self.entries)

    def __getitem__(self, index: int) -> Entry:
        return self.entries[index]

    # --- writing -------------------------------------------------------------------------
    def add_text(self, text: str) -> bool:
        """Record a copied string. Empty and whitespace-only copies are not history."""
        if not text or not text.strip():
            return False
        return self._add(Entry(kind="text", text=text))

    def add_image(self, path: str) -> bool:
        if not path:
            return False
        return self._add(Entry(kind="image", path=str(path)))

    def _add(self, entry: Entry) -> bool:
        for existing in self.entries:
            if existing.kind == entry.kind and existing.key == entry.key:
                # Same content copied again: it moves to the top and keeps its pin.
                self.entries.remove(existing)
                existing.when = entry.when
                self.entries.insert(0, existing)
                return True
        self.entries.insert(0, entry)
        self._trim()
        return True

    def _trim(self) -> None:
        while len(self.entries) > self._limit:
            for index in range(len(self.entries) - 1, -1, -1):
                if not self.entries[index].pinned:
                    del self.entries[index]
                    break
            else:                                   # every entry is pinned: keep them all
                return

    def toggle_pin(self, index: int) -> bool:
        if not 0 <= index < len(self.entries):
            return False
        self.entries[index].pinned = not self.entries[index].pinned
        self.save_pinned()
        return True

    def remove(self, index: int) -> bool:
        if not 0 <= index < len(self.entries):
            return False
        was_pinned = self.entries[index].pinned
        del self.entries[index]
        if was_pinned:
            self.save_pinned()
        return True

    def clear(self) -> int:
        """"Очистить все" — everything but the pinned entries. Returns how many were removed."""
        before = len(self.entries)
        self.entries = [entry for entry in self.entries if entry.pinned]
        return before - len(self.entries)

    # --- persistence ---------------------------------------------------------------------
    def _load_pinned(self) -> list[Entry]:
        try:
            data = json.loads(pinned_path(self._home).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        out = []
        for item in data if isinstance(data, list) else []:
            if not isinstance(item, dict) or item.get("kind") not in ("text", "image"):
                continue
            out.append(Entry(kind=item["kind"], text=item.get("text", ""),
                             path=item.get("path", ""), pinned=True,
                             when=float(item.get("when") or time.time())))
        return out[:self._limit]

    def save_pinned(self) -> Path:
        """Only pinned entries reach the disk. The rest die with the session, as they should."""
        path = pinned_path(self._home)
        path.parent.mkdir(parents=True, exist_ok=True)
        body = json.dumps([{"kind": e.kind, "text": e.text, "path": e.path, "when": e.when}
                           for e in self.entries if e.pinned], ensure_ascii=False, indent=1)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(body, encoding="utf-8")
        os.replace(tmp, path)
        return path
