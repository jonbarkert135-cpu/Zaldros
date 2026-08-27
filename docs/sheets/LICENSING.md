# Zaldros Sheets — licence obligations

LibreOffice core is offered under **MPL-2.0**, with **LGPLv3+** and **GPLv3** parts from its
history; the repository ships `COPYING` (GPLv3), `COPYING.LGPL` (LGPLv3) and `COPYING.MPL`
(MPL-2.0), and <https://www.libreoffice.org/licenses/> states the MPL-2.0 position.

Three integration modes carry three different obligations:

| Mode | Obligation |
| --- | --- |
| **Separate process over a UNO socket** (what we do) | No linking, so no copyleft reaches our Qt/QML code. We still carry the ordinary obligations of *redistributing the LibreOffice packages* inside the ISO: keep their licence files, and make the corresponding source available like any other GPL/MPL package in an Ubuntu-derived image. |
| Linking LOK into our binary | MPL-2.0 is file-level copyleft: our own new files stay ours, but the LGPLv3 combined-work rules apply to the LibreOffice libraries — users must be able to relink against a modified engine, and the licence texts and source offer must ship. Dynamic linking keeps this clean; static linking into one binary does not. Relevant if phase 2 (the tile view) links LOK. |
| Shipping a fork of core | Full GPLv3 corresponding-source duty for the whole fork plus MPL-2.0 for modified files. Rejected in ADR-0013 for engineering reasons; the licence weight is a second reason. |

## What this repository must do

1. Ship LibreOffice as **unmodified distribution packages**. Any patch we ever need goes upstream
   or into a package patch that is published with the image sources.
2. Record the components in `THIRD_PARTY_LICENSES.md` with their licences, the same way the
   cursor pack and the icon and font packs are recorded.
3. Keep `docs/VISUAL_LICENSE_AUDIT.md`'s rule in force for the UI: **no Microsoft code, fonts,
   icons or artwork.** Excel screenshots are used to *measure* geometry and to compare against;
   nothing is traced, extracted or embedded. The ribbon icons will be our own drawings or the
   MIT-licensed Fluent UI System Icons already vendored.
4. When phase 2 starts, revisit this file before the first line of LOK linking code.

Sources: <https://www.libreoffice.org/licenses/>,
<https://github.com/LibreOffice/core/blob/master/COPYING.MPL>,
<https://github.com/LibreOffice/core/blob/master/COPYING>,
<https://www.mozilla.org/en-US/MPL/2.0/FAQ/> (Q11 on Larger Works).
