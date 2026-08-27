"""The bridge from Zaldros Sheets to the spreadsheet engine.

Zaldros Sheets computes nothing. Every value, every formula result, every file read and written
comes from LibreOffice Calc, running as a headless child process we talk to over a local UNO
socket (see docs/state/decisions/ADR-0013-sheets-runs-on-libreoffice.md).

The UNO bindings (`import uno`) are built against the distribution's own Python, so this module
has to run under that interpreter — on Debian/Ubuntu the one `python3-uno` was built for. It
imports lazily and says exactly what is missing when it is missing, rather than failing with an
ImportError halfway through opening a user's file.
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

#: Engine filter names. These are the engine's own strings; do not invent new ones.
FILTERS = {
    ".xlsx": "Calc MS Excel 2007 XML",
    ".xlsm": "Calc MS Excel 2007 VBA XML",
    ".xls": "MS Excel 97",
    ".ods": "calc8",
    ".csv": "Text - txt - csv (StarCalc)",
}

CONNECT_TIMEOUT = 60.0


class EngineError(RuntimeError):
    """The engine could not be started, reached, or asked to do something."""


@dataclass(frozen=True)
class Cell:
    """One cell as the engine reports it. `value` is never computed by us."""

    row: int
    column: int
    formula: str
    value: float
    text: str

    @property
    def kind(self) -> str:
        if self.formula.startswith("="):
            return "formula"
        if not self.formula:
            return "empty"
        if self.text and self.value == 0 and not _looks_numeric(self.formula):
            return "text"
        return "number"


def _looks_numeric(raw: str) -> bool:
    try:
        float(raw.replace(",", "."))
    except ValueError:
        return False
    return True


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def soffice_path() -> str | None:
    """Where the engine is, or None. Never guess a path that may not exist."""
    return shutil.which("soffice") or shutil.which("libreoffice")


def uno_available() -> bool:
    try:
        import uno  # noqa: F401
    except Exception:
        return False
    return True


class Workbook:
    """One open document. All state lives in the engine; this is a handle, not a copy."""

    def __init__(self, engine: "CalcEngine", document) -> None:
        self._engine = engine
        self._doc = document

    # --- structure ---------------------------------------------------------------------------
    @property
    def sheet_names(self) -> list[str]:
        return list(self._doc.Sheets.ElementNames)

    def _sheet(self, sheet: int | str):
        try:
            if isinstance(sheet, str):
                return self._doc.Sheets.getByName(sheet)
            return self._doc.Sheets.getByIndex(sheet)
        except Exception as exc:  # the engine names the real problem; pass it on
            raise EngineError(f"no such sheet {sheet!r}: {exc}") from exc

    # --- cells -------------------------------------------------------------------------------
    def cell(self, row: int, column: int, sheet: int | str = 0) -> Cell:
        target = self._sheet(sheet).getCellByPosition(column, row)
        return Cell(row=row, column=column, formula=target.getFormula(),
                    value=float(target.getValue()), text=target.getString())

    def region(self, rows: int, columns: int, sheet: int | str = 0) -> list[list[Cell]]:
        """The top-left `rows` x `columns` block — what a grid view actually needs."""
        page = self._sheet(sheet)
        out: list[list[Cell]] = []
        for row in range(rows):
            line = []
            for column in range(columns):
                target = page.getCellByPosition(column, row)
                line.append(Cell(row=row, column=column, formula=target.getFormula(),
                                 value=float(target.getValue()), text=target.getString()))
            out.append(line)
        return out

    def set_value(self, row: int, column: int, value: float, sheet: int | str = 0) -> Cell:
        self._sheet(sheet).getCellByPosition(column, row).setValue(float(value))
        return self.cell(row, column, sheet)

    def set_text(self, row: int, column: int, text: str, sheet: int | str = 0) -> Cell:
        self._sheet(sheet).getCellByPosition(column, row).setString(str(text))
        return self.cell(row, column, sheet)

    def set_formula(self, row: int, column: int, formula: str, sheet: int | str = 0) -> Cell:
        """Set a formula and return what the engine made of it — including its own errors."""
        self._sheet(sheet).getCellByPosition(column, row).setFormula(formula)
        return self.cell(row, column, sheet)

    def set_input(self, row: int, column: int, raw: str, sheet: int | str = 0) -> Cell:
        """What typing into a cell does: the engine decides number, text or formula."""
        self._sheet(sheet).getCellByPosition(column, row).setFormula(raw)
        return self.cell(row, column, sheet)

    # --- files -------------------------------------------------------------------------------
    def save_as(self, path: str | os.PathLike[str], *, keep_open: bool = True) -> Path:
        target = Path(path).expanduser().resolve()
        suffix = target.suffix.lower()
        if suffix not in FILTERS:
            raise EngineError(f"unknown spreadsheet format {suffix!r}; "
                              f"known: {', '.join(sorted(FILTERS))}")
        args = (self._engine._property("FilterName", FILTERS[suffix]),)
        try:
            if keep_open:
                self._doc.storeToURL(target.as_uri(), args)
            else:
                self._doc.storeAsURL(target.as_uri(), args)
        except Exception as exc:
            raise EngineError(f"the engine refused to write {target}: {exc}") from exc
        if not target.exists():
            raise EngineError(f"the engine reported success but {target} does not exist")
        return target

    def close(self) -> None:
        try:
            self._doc.close(False)
        except Exception:
            pass


class CalcEngine:
    """The headless LibreOffice process plus the UNO connection to it."""

    def __init__(self, *, profile: str | os.PathLike[str] | None = None,
                 port: int | None = None) -> None:
        self._profile = Path(profile) if profile else Path(tempfile.mkdtemp(prefix="zaldros-sheets-"))
        self._port = port or _free_port()
        self._process: subprocess.Popen | None = None
        self._context = None
        self._desktop = None

    # --- lifecycle ---------------------------------------------------------------------------
    def start(self, timeout: float = CONNECT_TIMEOUT) -> "CalcEngine":
        binary = soffice_path()
        if binary is None:
            raise EngineError("the spreadsheet engine is not installed: no soffice on PATH "
                              "(package libreoffice-calc-nogui)")
        if not uno_available():
            raise EngineError("the UNO bridge is missing: `import uno` failed. Zaldros Sheets "
                              "must run under the interpreter python3-uno was built for")
        self._profile.mkdir(parents=True, exist_ok=True)
        self._process = subprocess.Popen(
            [binary, "--headless", "--invisible", "--nologo", "--norestore",
             f"-env:UserInstallation={self._profile.resolve().as_uri()}",
             f"--accept=socket,host=127.0.0.1,port={self._port};urp;StarOffice.ComponentContext"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        self._connect(timeout)
        return self

    def _connect(self, timeout: float) -> None:
        import uno

        local = uno.getComponentContext()
        resolver = local.ServiceManager.createInstanceWithContext(
            "com.sun.star.bridge.UnoUrlResolver", local)
        url = (f"uno:socket,host=127.0.0.1,port={self._port};urp;"
               "StarOffice.ComponentContext")
        deadline = time.monotonic() + timeout
        last = ""
        while time.monotonic() < deadline:
            if self._process is not None and self._process.poll() is not None:
                raise EngineError(f"the engine exited with code {self._process.returncode} "
                                  "before it accepted a connection")
            try:
                self._context = resolver.resolve(url)
                break
            except Exception as exc:
                last = str(exc)
                time.sleep(0.25)
        else:
            raise EngineError(f"the engine did not accept a UNO connection within {timeout:.0f}s "
                              f"on port {self._port}: {last}")
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

    def __enter__(self) -> "CalcEngine":
        return self.start()

    def __exit__(self, *_exc) -> None:
        self.stop()

    # --- documents ---------------------------------------------------------------------------
    def _property(self, name: str, value):
        # `from com.sun.star.beans import PropertyValue` only resolves through pyuno's import
        # hook and fails with "No module named 'com'" when the hook is not primed in this
        # interpreter; createUnoStruct is the documented, always-available way.
        import uno

        item = uno.createUnoStruct("com.sun.star.beans.PropertyValue")
        item.Name = name
        item.Value = value
        return item

    def _require_desktop(self):
        if self._desktop is None:
            raise EngineError("the engine is not running; call start() first")
        return self._desktop

    def new_workbook(self) -> Workbook:
        document = self._require_desktop().loadComponentFromURL(
            "private:factory/scalc", "_blank", 0, (self._property("Hidden", True),))
        return Workbook(self, document)

    def open(self, path: str | os.PathLike[str]) -> Workbook:
        source = Path(path).expanduser().resolve()
        if not source.exists():
            raise EngineError(f"no such spreadsheet: {source}")
        try:
            document = self._require_desktop().loadComponentFromURL(
                source.as_uri(), "_blank", 0, (self._property("Hidden", True),))
        except Exception as exc:
            raise EngineError(f"the engine could not open {source}: {exc}") from exc
        if document is None:
            raise EngineError(f"the engine returned no document for {source}")
        return Workbook(self, document)
