# Excel → Zaldros Sheets feature matrix

What a user coming from Excel gets, and what they do not. The engine column is LibreOffice Calc;
the UI column is what Zaldros Sheets has actually built. Nothing is marked done here because it is
planned — only because it exists and a test or a screenshot proves it.

Researched 2026-08-28 against upstream documentation; every "gap" row carries its source. Rows
marked **unverified** are honest gaps in our own research, not claims.

| Area | Engine (Calc) | Excel parity | Zaldros Sheets UI |
| --- | --- | --- | --- |
| Formulas and functions | 300+ functions; XLOOKUP, LET, LAMBDA, SORT, FILTER, UNIQUE, SEQUENCE since 24.8/25.8 | Close. Spill/dynamic-array semantics still differ from Excel 365 | ✅ formula bar, entry, engine-computed result (slice 1) |
| Number formats, cell styles, borders, merges | full | good; some Excel-only flags survive only through the OOXML "grab bag" | ⏳ |
| Charts | `chart2`, ~15–20 types | **gap**: box-and-whisker, funnel, Pareto, sunburst, treemap, waterfall round-trip as placeholders, not editable; region-map geo data is lost | ⏳ needs the LOK tile view |
| Excel tables (structured) | table styles, XML storage | **unverified** — structured references and totals row not checked | ⏳ |
| Pivot tables | DataPilot, calculated fields (26.8) | **gap**: no slicers (open enhancement bug), no multi-hierarchy fields | ⏳ |
| Filtering and sorting | AutoFilter, standard filter, multi-key sort | good | ⏳ |
| Conditional formatting | rule-based, style-linked | icon-set / data-bar depth vs Excel **unverified** | ⏳ |
| Data validation | `ScValidationData`, OOXML import | list/number/date/custom present at filter level; UI parity **unverified** | ⏳ |
| Power Query | **absent** — only the much smaller "Data Provider" (CSV/HTML/XML with a few transforms) | **hard gap** | ❌ not offered |
| Macros / VBA | LO Basic with `Option VBASupport 1` | partial: upstream says the VBA object model is "not complete"; no VBA bytecode, no COM automation | ❌ not offered in slice 1 |
| Co-authoring | not in desktop LibreOffice (only Collabora Online) | **hard gap** | ❌ |
| Comments | cell notes; threaded XLSX comments landing upstream | verify against the shipped release before promising | ⏳ |
| Print / PDF | full pipeline | fine-grained parity **unverified** | ⏳ |
| Add-ins | UNO add-ins | `.xlam` Excel add-ins do not load | ❌ |
| XLSX / XLS / CSV / ODS files | full filters | the compatibility everything else rests on | ✅ open and save XLSX (slice 1) |

Legend: ✅ built and tested · ⏳ planned · ❌ will not exist, say so to users.

Sources for the gap rows: LibreOffice help pages for XLOOKUP/LET and the Data Provider; the 26.8
release notes for chart round-tripping and pivot calculated fields; TDF bug 119807 (slicers);
`text/sbasic/shared/vbasupport.html` for the VBA compatibility wording; the Document Foundation
post on the OOXML "grab bag" for why some round-trips preserve without editing.
