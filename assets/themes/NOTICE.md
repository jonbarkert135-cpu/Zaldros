# Borrowed theme assets

Everything in this directory came from somewhere else. It is vendored, unmodified, with its
licence, so that an ISO build is reproducible without reaching out to a store at build time
(pling download links are signed and expire).

| Asset | Upstream | Version | Author | Licence | Used for |
| --- | --- | --- | --- | --- | --- |
| `aurorae/Windows-Eleven` | store.kde.org/p/1977804 | 1.6.1 (rc 1.3.2) | zayronXIO | GPL-3.0 | KWin window decoration, light variant |
| `aurorae/Windows-Eleven-Dark` | store.kde.org/p/1984455 | 1.6.9 (rc 1.2.4) | zayronXIO | GPL-3.0 | KWin window decoration, dark variant |
| `icons/Windows-Eleven-icons-4.8.8.tar.xz` | store.kde.org/p/1977340 | 4.8.8 | zayronXIO, after yeyushengfan258 and kuroe-hanako | GPL-3.0 | fallback icon theme for KDE/GTK applications |

Obligations we meet: the files are unmodified, the notices are installed into
`/usr/share/doc/zaldros/licenses/`, and the ISO ships the same files it was built from — GPL-3
source for an SVG theme is the SVG. If any of these is modified, it must be renamed and the change
recorded here.

The Aurorae themes are usable **because Aurorae is part of KWin, not of Plasma**: the engine lives
in `kwin-style-aurorae` and needs no plasmashell. Everything else in the two "windows-eleven"
Look-and-Feel packages (Plasma theme, plasmoids, panel layout, splash, SDDM) requires plasmashell
and is deliberately not used — see `docs/PLASMA_THEME_AUDIT.md`.
