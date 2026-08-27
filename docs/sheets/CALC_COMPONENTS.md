# What the engine already gives us

Everything below exists in LibreOffice and must never be reimplemented in Zaldros code. Module
paths are LibreOffice core's own; links are to upstream documentation, fetched 2026-08-28.

| Area | Where it lives in core | Notes |
| --- | --- | --- |
| Formula compiler and interpreter | `ScCompiler` (`sc/source/core/tool/compiler.cxx`), `ScInterpreter` (`sc/inc/interpre.hxx`), `ScFormulaCell` (`sc/inc/formulacell.hxx`) | 300+ functions, largely ODF OpenFormula. XLOOKUP and LET arrived in 24.8 and are explicitly outside OpenFormula. |
| XLSX / XLSM import and export | `oox/` (`oox::core::XmlFilterBase`) plus `sc/source/filter/oox/excelfilter.hxx` | The OOXML filter Excel compatibility rests on. |
| XLS (BIFF), CSV, ODS | `sc/source/filter/`, `ScOrcusFiltersImpl` (`importCSV`, `importXLSX`, `importODS`), `ScImportExport` (`sc/inc/impex.hxx`) | |
| Charts | `chart2/` — `ChartModel`, `ChartView` (via `drawinglayer`), `ChartController` | ~15–20 native types. |
| Pivot tables ("DataPilot") | `ScDPObject`/`ScDPSource` (`sc/inc/dptabsrc.hxx`), UNO wrappers in `sc/inc/dapiuno.hxx` | |
| AutoFilter and sort | `oox::xls::AutoFilter` (`sc/source/filter/oox/autofilterbuffer.hxx`), `ScDBFunc::UISort`, `ScDBFunc::ToggleAutoFilter` (`sc/inc/dbfunc.hxx`) | |
| Conditional formatting | `ScConditionalFormat`, `ScConditionalFormatList` | |
| Cell styles | `ScStyleSheet` (`sc/inc/stlsheet.hxx`); UNO families `CellStyles`, `GraphicStyles`, `PageStyles` (`sc/source/ui/unoobj/styleuno.cxx`) | |
| Data validation | `ScValidationData`, `oox::xls::DataValidationsContextBase` | |
| Print and PDF export | the shared `XRenderable` → `drawinglayer` pipeline | |
| Macros | LibreOffice Basic with `Option VBASupport 1` | Partial VBA object model — see the feature matrix. |

## Driving the ribbon: `.uno:` commands

The ribbon must dispatch the engine's own commands, not reimplement their effects. Taken from
LibreOffice's help repository (`helpers/uno-commands.csv`, `helpers/longnames_commands.csv`), not
from memory:

| Excel action | `.uno:` command |
| --- | --- |
| Bold | `.uno:Bold` (`.uno:BoldCJK`, `.uno:BoldCTL` for CJK/CTL runs) |
| Cell fill colour | `.uno:BackgroundColor` |
| Merge & centre | `.uno:MergeCells`, toggle `.uno:ToggleMergeCells`, undo `.uno:SplitCell` |
| Insert chart | `.uno:InsertObjectChart` |
| AutoFilter | `.uno:DataFilterAutoFilter` (generic form `.uno:AutoFilter`) |
| Standard filter | `.uno:DataFilterStandardFilter` |
| Sort dialog | `.uno:DataSort` |
| Freeze panes | `.uno:FreezePanes` |
| Conditional formatting dialog | `.uno:ConditionalFormatDialog` |

Sources: <https://github.com/LibreOffice/help/blob/master/helpers/uno-commands.csv>,
<https://github.com/LibreOffice/help/blob/master/helpers/longnames_commands.csv>,
<https://docs.libreoffice.org/sc.html>.

Anything not in that CSV is not a command we may invent; look it up before wiring a button.
