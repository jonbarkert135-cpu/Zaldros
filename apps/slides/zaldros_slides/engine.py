# SPDX-License-Identifier: GPL-3.0-or-later
"""The bridge from Zaldros Slides to the presentation engine.

Same arrangement as Sheets (ADR-0013) and Writer (ADR-0020): our window, LibreOffice Impress's
engine, over a local UNO socket. Slides, layouts, text boxes, notes, transitions, PPTX/ODP and
PDF export are all its work.

Unlike Writer, this one is verifiable here: `libreoffice-impress-nogui` is installed in the build
sandbox, so the tests below really start the engine and really open PPTX files.
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

FILTERS = {
    ".pptx": "Impress MS PowerPoint 2007 XML",
    ".ppt": "MS PowerPoint 97",
    ".odp": "impress8",
    ".pdf": "impress_pdf_Export",
}

#: Impress's own layout numbers. Not invented: these are the `Layout` property values.
LAYOUTS = {0: "Титульный слайд", 1: "Заголовок и содержимое", 2: "Заголовок и текст",
           19: "Только заголовок", 20: "Пустой слайд"}

#: Slide transitions. Impress 7.4 exposes them as `TransitionType` (the SMIL transition family),
#: **not** as the `FadeEffect` property the older API documents — asked of a running engine, which
#: does not have `FadeEffect` on a draw page at all. The names are PowerPoint's.
TRANSITIONS = {0: "Нет", 1: "Шторки", 8: "Прямоугольник", 26: "Растворение", 46: "Появление"}

CONNECT_TIMEOUT = 60.0


class EngineError(RuntimeError):
    """The engine could not be started, reached, or asked to do something."""


@dataclass(frozen=True)
class Slide:
    """One slide as the engine reports it."""

    index: int
    name: str
    title: str
    body: str
    layout: int
    notes: str = ""
    shapes: int = 0

    @property
    def layout_name(self) -> str:
        return LAYOUTS.get(self.layout, f"макет {self.layout}")


def soffice_path() -> str | None:
    return shutil.which("soffice") or shutil.which("libreoffice")


def uno_available() -> bool:
    try:
        import uno  # noqa: F401
    except Exception:
        return False
    return True


def impress_available() -> bool:
    """True only when the Impress component is installed — `soffice` alone proves nothing."""
    if soffice_path() is None:
        return False
    program = Path(soffice_path()).resolve().parent
    for candidate in (program / "libsdlo.so", Path("/usr/lib/libreoffice/program/libsdlo.so")):
        if candidate.exists():
            return True
    return False


def _is_notes_shape(shape) -> bool:
    """The notes box answers to its *shape type*, not to `supportsService`.

    `supportsService("com.sun.star.presentation.NotesShape")` returns False on the very shape
    whose `getShapeType()` is that exact string — found by asking a running Impress rather than
    by trusting the documentation.
    """
    try:
        return str(shape.getShapeType()) == "com.sun.star.presentation.NotesShape"
    except Exception:
        return False


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


class Presentation:
    """One open presentation. The slides live in the engine; this is a handle."""

    def __init__(self, engine: "ImpressEngine", document) -> None:
        self._engine = engine
        self._doc = document

    # --- reading -------------------------------------------------------------------------
    def __len__(self) -> int:
        return int(self._doc.getDrawPages().getCount())

    def slides(self) -> list[Slide]:
        out: list[Slide] = []
        pages = self._doc.getDrawPages()
        for index in range(pages.getCount()):
            page = pages.getByIndex(index)
            title, body = self._text_of(page)
            out.append(Slide(index=index, name=str(page.Name), title=title, body=body,
                             layout=int(getattr(page, "Layout", 20)),
                             notes=self._notes_of(page), shapes=int(page.getCount())))
        return out

    @staticmethod
    def _text_of(page) -> tuple[str, str]:
        title, body = "", []
        for position in range(page.getCount()):
            shape = page.getByIndex(position)
            if not hasattr(shape, "getString"):
                continue
            text = shape.getString()
            if not text:
                continue
            if shape.supportsService("com.sun.star.presentation.TitleTextShape"):
                title = text
            else:
                body.append(text)
        return title, "\n".join(body)

    @staticmethod
    def _notes_of(page) -> str:
        try:
            notes_page = page.getNotesPage()
        except Exception:
            return ""
        parts = []
        for position in range(notes_page.getCount()):
            shape = notes_page.getByIndex(position)
            if _is_notes_shape(shape):
                parts.append(shape.getString())
        return "\n".join(part for part in parts if part)

    # --- writing -------------------------------------------------------------------------
    def add_slide(self, index: int | None = None, layout: int = 1) -> int:
        pages = self._doc.getDrawPages()
        position = pages.getCount() if index is None else max(0, min(index, pages.getCount()))
        pages.insertNewByIndex(position)
        page = pages.getByIndex(position)
        try:
            page.Layout = int(layout)
        except Exception as exc:
            raise EngineError(f"движок отказал в макете {layout}: {exc}") from exc
        return position

    def remove_slide(self, index: int) -> None:
        pages = self._doc.getDrawPages()
        if not (0 <= index < pages.getCount()):
            raise EngineError(f"нет слайда с номером {index}")
        pages.remove(pages.getByIndex(index))

    def set_layout(self, index: int, layout: int) -> None:
        """Layouts are the engine's numbered placeholder sets. A slide made with the blank
        layout has nowhere to put a title, which is why this exists as its own step."""
        page = self._page(index)
        try:
            page.Layout = int(layout)
        except Exception as exc:
            raise EngineError(f"движок отказал в макете {layout}: {exc}") from exc

    def set_text(self, index: int, title: str | None = None, body: str | None = None) -> None:
        """Fill the layout's own placeholders. If a layout has no body placeholder, that is the
        engine's answer and it is reported, not worked around by drawing a free text box."""
        page = self._page(index)
        wrote_title = wrote_body = False
        for position in range(page.getCount()):
            shape = page.getByIndex(position)
            if not hasattr(shape, "setString"):
                continue
            if title is not None and shape.supportsService(
                    "com.sun.star.presentation.TitleTextShape"):
                shape.setString(title)
                wrote_title = True
            elif body is not None and shape.supportsService(
                    "com.sun.star.presentation.OutlinerShape"):
                shape.setString(body)
                wrote_body = True
            elif body is not None and not wrote_body and shape.supportsService(
                    "com.sun.star.presentation.SubtitleTextShape"):
                shape.setString(body)
                wrote_body = True
        if title is not None and not wrote_title:
            raise EngineError(f"у слайда {index} нет заполнителя заголовка в этом макете")
        if body is not None and not wrote_body:
            raise EngineError(f"у слайда {index} нет заполнителя текста в этом макете")

    def set_notes(self, index: int, text: str) -> None:
        page = self._page(index)
        notes_page = page.getNotesPage()
        for position in range(notes_page.getCount()):
            shape = notes_page.getByIndex(position)
            if _is_notes_shape(shape):
                shape.setString(text)
                return
        raise EngineError(f"у слайда {index} нет области заметок")

    def set_transition(self, index: int, effect: int) -> None:
        page = self._page(index)
        try:
            page.TransitionType = int(effect)
        except Exception as exc:
            raise EngineError(f"движок отказал в переходе {effect}: {exc}") from exc

    def transition(self, index: int) -> int:
        return int(getattr(self._page(index), "TransitionType", 0))

    def _page(self, index: int):
        pages = self._doc.getDrawPages()
        if not (0 <= index < pages.getCount()):
            raise EngineError(f"нет слайда с номером {index}")
        return pages.getByIndex(index)

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

    def close(self) -> None:
        try:
            self._doc.close(False)
        except Exception:
            pass


class ImpressEngine:
    """The headless LibreOffice process plus the UNO connection to it."""

    def __init__(self, *, profile: str | os.PathLike[str] | None = None,
                 port: int | None = None) -> None:
        self._profile = Path(profile) if profile else Path(
            tempfile.mkdtemp(prefix="zaldros-slides-"))
        self._port = port or _free_port()
        self._process: subprocess.Popen | None = None
        self._context = None
        self._desktop = None

    def start(self, timeout: float = CONNECT_TIMEOUT) -> "ImpressEngine":
        binary = soffice_path()
        if binary is None:
            raise EngineError("движок не установлен: нет soffice в PATH "
                              "(пакет libreoffice-impress-nogui)")
        if not uno_available():
            raise EngineError("нет моста UNO: `import uno` не сработал")
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
            raise EngineError(f"движок не принял соединение UNO за {timeout:.0f} с: {last}")
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

    def __enter__(self) -> "ImpressEngine":
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

    def new_presentation(self) -> Presentation:
        if not impress_available():
            raise EngineError("движок Impress не установлен: нет libsdlo.so "
                              "(пакет libreoffice-impress-nogui)")
        try:
            document = self._require_desktop().loadComponentFromURL(
                "private:factory/simpress", "_blank", 0, (self._property("Hidden", True),))
        except EngineError:
            raise
        except Exception as exc:
            raise EngineError(f"движок не создал презентацию: {exc}") from exc
        if document is None:
            raise EngineError("движок не вернул презентацию")
        return Presentation(self, document)

    def open(self, path: str | os.PathLike[str]) -> Presentation:
        source = Path(path).expanduser().resolve()
        if not source.exists():
            raise EngineError(f"нет такой презентации: {source}")
        try:
            document = self._require_desktop().loadComponentFromURL(
                source.as_uri(), "_blank", 0, (self._property("Hidden", True),))
        except Exception as exc:
            raise EngineError(f"движок не смог открыть {source}: {exc}") from exc
        if document is None:
            raise EngineError(f"движок не вернул документ для {source}")
        return Presentation(self, document)
