# Building and running Zaldros Sheets

## Runtime pieces

| Piece | Package on the ISO | Why |
| --- | --- | --- |
| Spreadsheet engine | `libreoffice-calc-nogui`, `libreoffice-core-nogui` | formulas, XLSX/XLS/CSV/ODS, charts |
| UNO bridge | `python3-uno` | the channel our bridge talks over |
| UI | PySide6 (Qt 6), same runtime as the shell | our own window |

`python3-uno` is compiled against the distribution's Python. Zaldros Sheets therefore runs under
**the system interpreter**, not a private virtualenv — a venv without
`--system-site-packages` cannot `import uno`, and the app says so instead of failing obscurely.

## Running it

```
cd apps/sheets
python3 -m zaldros_sheets run                       # empty workbook
python3 -m zaldros_sheets run --open book.xlsx
QT_QPA_PLATFORM=offscreen python3 -m zaldros_sheets render --out sheets.png
QT_QPA_PLATFORM=offscreen python3 -m zaldros_sheets render --open book.xlsx --out sheets.png --dark
```

## Tests

```
cd apps/sheets && python3 -m pytest tests -q
```

* `tests/test_engine.py` drives a **real** headless LibreOffice: formula, error, XLSX round trip.
  It skips — loudly — when the engine or the UNO bridge is absent, because a green run without an
  engine would prove nothing.
* `tests/test_ui.py` renders the window offscreen and measures it against
  `system/theme/excel-reference.json`.

CI runs both in the `sheets` job, on the runner's own Python with `python3-uno` from apt.
