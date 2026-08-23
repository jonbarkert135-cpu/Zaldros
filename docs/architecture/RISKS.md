# Risk register

| # | Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|---|
| R1 | Scope: a full desktop OS is a multi-year, multi-person effort | Project stalls | High | Phase gates; reuse mature OSS (KWin/Plasma); ship a usable v0.1 early |
| R2 | Trademark/IP: Windows look-alike + Microsoft assets | Legal takedown | Medium | No MS binaries/fonts/icons/wallpapers in repo; own icon set + open fonts; "not affiliated with Microsoft" notice |
| R3 | Name collision with the existing Bedrock OS meta-distribution (bedrocklinux.org) | Brand confusion, SEO | High | Flagged to the owner; decide final public name before any release |
| R4 | Fedora/bootc path is newer than apt tooling; fewer tutorials | Slower dev | Medium | Documented Debian fallback; keep OS build declarative and portable |
| R5 | Plasma upstream changes break our shell components | Rework | Medium | Pin Plasma version per release; CI against next Plasma before upgrading |
| R6 | Performance targets unmet on old hardware | Missed goal | Medium | Bedrock Legacy profile; measurement contract on every milestone |
| R7 | `.deb`-only vendor software unavailable | User complaints | Medium | Flatpak first, distrobox documented path |
| R8 | Hardware/driver regressions (NVIDIA, HDR, fingerprint) | Support load | High | Hardware test matrix from Phase 1; ship an "known working hardware" list |
| R9 | Single maintainer / bus factor | Project death | High | Everything in git, documented ADRs, reproducible CI builds |
