# SPDX-License-Identifier: GPL-3.0-or-later
"""The bridge from Zaldros Writer to the word-processing engine.

Zaldros Writer formats nothing itself. Every paragraph, style, table, image, page count and PDF
comes from LibreOffice Writer, running headless and reached over a local UNO socket — the same
arrangement Sheets uses for Calc (ADR-0013), for the same reason: writing a word processor is a
decade of work and there is already a good one under a licence we can build on.

Two entry points, and the difference matters:

* `WriterEngine` — a live document. Needs `libreoffice-writer-nogui` **and** the UNO bridge.
* `convert()` — file in, file out, through `soffice --convert-to`. No UNO, no live document; it
  is what «Экспорт в PDF» falls back to, and it is honest about being a conversion rather than an
  edit.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

#: The engine's own filter names. Not invented here — these strings come from LibreOffice.
FILTERS = {
    ".docx": "MS Word 2007 XML",
    ".doc": "MS Word 97",
    ".odt": "writer8",
    ".rtf": "Rich Text Format",
    ".txt": "Text",
    ".pdf": "writer_pdf_Export",
}

CONNECT_TIMEOUT = 60.0


class EngineError(RuntimeError):
    """The engine could not be started, reached, or asked to do something."""


@dataclass(frozen=True)
class Paragraph:
    """One paragraph as the engine reports it."""

    index: int
    text: str
    style: str
    bold: bool = False
    italic: bool = False
    underline: bool = False
    size: float = 0.0
    alignment: int = 0


def soffice_path() -> str | None:
    return shutil.which("soffice") or shutil.which("libreoffice")


def uno_available() -> bool:
    try:
        import uno  # noqa: F401
    except Exception:
        return False
    return True


def writer_available() -> bool:
    """True only when the Writer component is really installed.

    `soffice` on PATH proves nothing: a machine can have `libreoffice-calc-nogui` and no Writer
    at all, which is exactly the case in our build sandbox. Asking the engine to make a `swriter`
    document is the only answer that cannot be wrong.
    """
    binary = soffice_path()
    if binary is None:
        return False
    program = Path(binary).resolve().parent
    for candidate in (program / "libswlo.so", Path("/usr/lib/libreoffice/program/libswlo.so")):
        if candidate.exists():
            return True
    return False


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def convert(source: str | os.PathLike[str], target_suffix: str,
            outdir: str | os.PathLike[str] | None = None, timeout: float = 120.0) -> Path:
    """Convert a file with the engine's own command line. Returns the file it really produced."""
    binary = soffice_path()
    if binary is None:
        raise EngineError("движок не установлен: soffice не найден в PATH "
                          "(пакет libreoffice-writer-nogui)")
    suffix = target_suffix if target_suffix.startswith(".") else f".{target_suffix}"
    if suffix not in FILTERS:
        raise EngineError(f"неизвестный формат {suffix!r}; известные: {', '.join(sorted(FILTERS))}")
    source_path = Path(source).expanduser().resolve()
    if not source_path.exists():
        raise EngineError(f"нет такого документа: {source_path}")
    destination = Path(outdir).expanduser().resolve() if outdir else source_path.parent
    profile = Path(tempfile.mkdtemp(prefix="zaldros-writer-"))
    result = subprocess.run(
        [binary, "--headless", "--norestore", f"-env:UserInstallation={profile.as_uri()}",
         "--convert-to", suffix.lstrip("."), "--outdir", str(destination), str(source_path)],
        capture_output=True, text=True, timeout=timeout)
    produced = destination / (source_path.stem + suffix)
    if not produced.exists():
        raise EngineError(f"движок не создал {produced}: "
                          f"{(result.stderr or result.stdout or '').strip()[:300]}")
    return produced


class Document:
    """One open document. The text lives in the engine; this is a handle, not a copy."""

    def __init__(self, engine: "WriterEngine", document) -> None:
        self._engine = engine
        self._doc = document

    # --- reading -------------------------------------------------------------------------
    @property
    def text(self) -> str:
        return self._doc.getText().getString()

    def paragraphs(self) -> list[Paragraph]:
        out: list[Paragraph] = []
        enumeration = self._doc.getText().createEnumeration()
        index = 0
        while enumeration.hasMoreElements():
            element = enumeration.nextElement()
            if not element.supportsService("com.sun.star.text.Paragraph"):
                index += 1
                continue
            out.append(Paragraph(
                index=index, text=element.getString(),
                style=str(getattr(element, "ParaStyleName", "")),
                bold=float(getattr(element, "CharWeight", 100)) > 100,
                italic=int(getattr(element, "CharPosture", 0)) != 0,
                underline=int(getattr(element, "CharUnderline", 0)) != 0,
                size=float(getattr(element, "CharHeight", 0)),
                alignment=int(getattr(element, "ParaAdjust", 0))))
            index += 1
        return out

    def page_count(self) -> int:
        """The engine's own pagination — the number in Word's status bar."""
        try:
            return int(self._doc.getCurrentController().PageCount)
        except Exception as exc:
            raise EngineError(f"движок не сообщил число страниц: {exc}") from exc

    def word_count(self) -> int:
        return len([word for word in self.text.split() if word])

    # --- writing -------------------------------------------------------------------------
    def append(self, text: str, style: str = "") -> None:
        body = self._doc.getText()
        cursor = body.createTextCursorByRange(body.getEnd())
        if style:
            cursor.ParaStyleName = style
        body.insertString(cursor, text, False)

    def append_paragraph(self, text: str = "", style: str = "") -> None:
        body = self._doc.getText()
        cursor = body.createTextCursorByRange(body.getEnd())
        body.insertControlCharacter(cursor, 0, False)      # PARAGRAPH_BREAK
        if style:
            cursor.ParaStyleName = style
        if text:
            body.insertString(cursor, text, False)

    def set_paragraph_style(self, index: int, style: str) -> None:
        """Apply a real Writer style — «Heading 1», not our own idea of bold text."""
        enumeration = self._doc.getText().createEnumeration()
        position = 0
        while enumeration.hasMoreElements():
            element = enumeration.nextElement()
            if not element.supportsService("com.sun.star.text.Paragraph"):
                continue
            if position == index:
                try:
                    element.ParaStyleName = style
                except Exception as exc:
                    raise EngineError(f"движок отказал в стиле {style!r}: {exc}") from exc
                return
            position += 1
        raise EngineError(f"нет абзаца с номером {index}")

    def set_character_format(self, index: int, bold: bool | None = None,
                             italic: bool | None = None, underline: bool | None = None,
                             size: float | None = None) -> None:
        enumeration = self._doc.getText().createEnumeration()
        position = 0
        while enumeration.hasMoreElements():
            element = enumeration.nextElement()
            if not element.supportsService("com.sun.star.text.Paragraph"):
                continue
            if position == index:
                if bold is not None:
                    element.CharWeight = 150.0 if bold else 100.0
                if italic is not None:
                    element.CharPosture = 2 if italic else 0
                if underline is not None:
                    element.CharUnderline = 1 if underline else 0
                if size is not None:
                    element.CharHeight = float(size)
                return
            position += 1
        raise EngineError(f"нет абзаца с номером {index}")

    def insert_table(self, rows: int, columns: int, values: list[list[str]] | None = None) -> None:
        table = self._doc.createInstance("com.sun.star.text.TextTable")
        table.initialize(max(1, rows), max(1, columns))
        body = self._doc.getText()
        body.insertTextContent(body.getEnd(), table, False)
        for row, line in enumerate(values or []):
            for column, value in enumerate(line):
                name = f"{chr(ord('A') + column)}{row + 1}"
                try:
                    table.getCellByName(name).setString(str(value))
                except Exception:
                    pass                       # a cell outside the table is skipped, not invented

    def insert_image(self, path: str | os.PathLike[str], width: int = 8000,
                     height: int = 6000) -> None:
        source = Path(path).expanduser().resolve()
        if not source.exists():
            raise EngineError(f"нет такого изображения: {source}")
        graphic = self._doc.createInstance("com.sun.star.text.TextGraphicObject")
        graphic.GraphicURL = source.as_uri()
        graphic.Width, graphic.Height = int(width), int(height)
        body = self._doc.getText()
        body.insertTextContent(body.getEnd(), graphic, False)

    def styles(self) -> list[str]:
        """The paragraph styles the engine really has — the «Стили» gallery is this list."""
        try:
            return list(self._doc.StyleFamilies.getByName("ParagraphStyles").ElementNames)
        except Exception:
            return []

    # --- files -------------------------------------------------------------------------
    def save_as(self, path: str | os.PathLike[str], *, keep_open: bool = True) -> Path:
        target = Path(path).expanduser().resolve()
        suffix = target.suffix.lower()
        if suffix not in FILTERS:
            raise EngineError(f"неизвестный формат {suffix!r}; известные: "
                              f"{', '.join(sorted(FILTERS))}")
        args = (self._engine._property("FilterName", FILTERS[suffix]),)
        try:
            if keep_open:
                self._doc.storeToURL(target.as_uri(), args)
            else:
                self._doc.storeAsURL(target.as_uri(), args)
        except Exception as exc:
            raise EngineError(f"движок отказался записать {target}: {exc}") from exc
        if not target.exists():
            raise EngineError(f"движок сообщил об успехе, но {target} не существует")
        return target

    def export_pdf(self, path: str | os.PathLike[str]) -> Path:
        return self.save_as(Path(path).with_suffix(".pdf"))

    def print_document(self, printer: str = "") -> None:
        """Печать через движок. Без очереди CUPS это ошибка, а не тихое ничего."""
        try:
            if printer:
                self._doc.setPrinter((self._engine._property("Name", printer),))
            self._doc.print_(())
        except Exception as exc:
            raise EngineError(f"движок не смог напечатать документ: {exc}") from exc

    def close(self) -> None:
        try:
            self._doc.close(False)
        except Exception:
            pass


class WriterEngine:
    """The headless LibreOffice process plus the UNO connection to it."""

    def __init__(self, *, profile: str | os.PathLike[str] | None = None,
                 port: int | None = None) -> None:
        self._profile = Path(profile) if profile else Path(
            tempfile.mkdtemp(prefix="zaldros-writer-"))
        self._port = port or _free_port()
        self._process: subprocess.Popen | None = None
        self._context = None
        self._desktop = None

    def start(self, timeout: float = CONNECT_TIMEOUT) -> "WriterEngine":
        binary = soffice_path()
        if binary is None:
            raise EngineError("движок не установлен: нет soffice в PATH "
                              "(пакет libreoffice-writer-nogui)")
        if not uno_available():
            raise EngineError("нет моста UNO: `import uno` не сработал. Zaldros Writer должен "
                              "запускаться тем интерпретатором, под который собран python3-uno")
        self._profile.mkdir(parents=True, exist_ok=True)
        self._process = subprocess.Popen(
            [binary, "--headless", "--invisible", "--nologo", "--norestore",
             f"-env:UserInstallation={self._profile.resolve().as_uri()}",
             f"--accept=socket,host=127.0.0.1,port={self._port};urp;StarOffice.ComponentContext"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self._connect(timeout)
        return self

    def _connect(self, timeout: float) -> None:
        import uno

        local = uno.getComponentContext()
        resolver = local.ServiceManager.createInstanceWithContext(
            "com.sun.star.bridge.UnoUrlResolver", local)
        url = f"uno:socket,host=127.0.0.1,port={self._port};urp;StarOffice.ComponentContext"
        deadline = time.monotonic() + timeout
        last = ""
        while time.monotonic() < deadline:
            if self._process is not None and self._process.poll() is not None:
                raise EngineError(f"движок вышел с кодом {self._process.returncode} до того, "
                                  "как принял соединение")
            try:
                self._context = resolver.resolve(url)
                break
            except Exception as exc:
                last = str(exc)
                time.sleep(0.25)
        else:
            raise EngineError(f"движок не принял соединение UNO за {timeout:.0f} с "
                              f"на порту {self._port}: {last}")
        self._desktop = self._context.ServiceManager.createInstanceWithContext(
            "com.sun.star.frame.Desktop", self._context)

    def stop(self) -> None:
        try:
            if self._desktop is not None:
                self._desktop.terminate()
        except Exception:
            pass
        if self._process is not None:
            try:
                self._process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._process.terminate()
        self._process = None
        self._context = None
        self._desktop = None

    def __enter__(self) -> "WriterEngine":
        return self.start()

    def __exit__(self, *_exc) -> None:
        self.stop()

    def _property(self, name: str, value):
        import uno

        item = uno.createUnoStruct("com.sun.star.beans.PropertyValue")
        item.Name = name
        item.Value = value
        return item

    def _require_desktop(self):
        if self._desktop is None:
            raise EngineError("движок не запущен; сначала start()")
        return self._desktop

    def new_document(self) -> Document:
        if not writer_available():
            # The engine's own message here is "type detection failed", which tells a user
            # nothing. The package that is missing is the fact worth reporting.
            raise EngineError("движок Writer не установлен: нет libswlo.so "
                              "(пакет libreoffice-writer-nogui)")
        try:
            document = self._require_desktop().loadComponentFromURL(
                "private:factory/swriter", "_blank", 0, (self._property("Hidden", True),))
        except EngineError:
            raise
        except Exception as exc:
            raise EngineError(f"движок не создал документ: {exc}") from exc
        if document is None:
            raise EngineError("движок не создал документ: вероятно, не установлен "
                              "libreoffice-writer-nogui")
        return Document(self, document)

    def open(self, path: str | os.PathLike[str]) -> Document:
        source = Path(path).expanduser().resolve()
        if not source.exists():
            raise EngineError(f"нет такого документа: {source}")
        try:
            document = self._require_desktop().loadComponentFromURL(
                source.as_uri(), "_blank", 0, (self._property("Hidden", True),))
        except Exception as exc:
            raise EngineError(f"движок не смог открыть {source}: {exc}") from exc
        if document is None:
            raise EngineError(f"движок не вернул документ для {source}")
        return Document(self, document)
