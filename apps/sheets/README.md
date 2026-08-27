# Zaldros Sheets

Our Excel-shaped UI on LibreOffice Calc's engine.

* Why it is built this way: `docs/state/decisions/ADR-0013-sheets-runs-on-libreoffice.md`
* Architecture and the LOK phase 2 plan: `docs/sheets/ARCHITECTURE.md`
* Measured Excel geometry: `system/theme/excel-reference.json`, sources in
  `assets/refs/excel/library.json`
* What Calc can and cannot do: `docs/sheets/EXCEL_FEATURE_MATRIX.md`
* How to run and test: `docs/sheets/BUILD.md`

**Zaldros Sheets computes nothing.** Every value, formula result and file read or written comes
from the engine. If Calc cannot do it, we say so instead of faking it.
