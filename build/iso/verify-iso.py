#!/usr/bin/env python3
"""Read xorriso's El Torito report and say plainly whether this ISO can boot UEFI firmware.

Why this exists: `build-iso.sh` used to prove the UEFI half of the image with
`xorriso -indev … -find /EFI -type f`, which printed

    xorriso : FAILURE : Cannot find path '/EFI' in loaded ISO image
    xorriso : aborting : -abort_on 'FAILURE' encountered 'FAILURE'

as the last two lines of *every successful build*. The probe was wrong, not the ISO:
`grub-mkrescue` does not put a /EFI directory in the ISO tree, it attaches a FAT image
(`/efi.img`) as the second El Torito boot image. So the build log ended with a scary FAILURE that
nobody could act on, while the fact we actually wanted — "there is a UEFI boot image" — was sitting
three lines above in the catalogue and was never checked.

Exit codes are the contract, because `build-iso.sh` acts on them:
  0  a UEFI boot image is listed in the catalogue      → verified
  1  the catalogue is readable and has no UEFI image   → this ISO cannot boot UEFI firmware
  3  the catalogue could not be read (no xorriso, empty file, unexpected output) → UNVERIFIED,
     which is neither a pass nor a failure and must never be printed as one
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# "El Torito boot img :   2  UEFI  y   none  0x0000  0x00   5760          72"
_BOOT_IMG = re.compile(
    r"^El Torito boot img\s*:\s*(?P<n>\d+)\s+(?P<platform>\S+)", re.MULTILINE)
# "El Torito img path :   2  /efi.img"
_IMG_PATH = re.compile(r"^El Torito img path\s*:\s*(?P<n>\d+)\s+(?P<path>\S+)", re.MULTILINE)
_CATALOG = re.compile(r"^El Torito catalog\s*:", re.MULTILINE)


def el_torito_verdict(report: str) -> tuple[int, str]:
    """Return (exit code, one line a human can act on) for a `-report_el_torito plain` dump."""
    text = report or ""
    images = {m.group("n"): m.group("platform").upper() for m in _BOOT_IMG.finditer(text)}
    paths = {m.group("n"): m.group("path") for m in _IMG_PATH.finditer(text)}
    if not images:
        if _CATALOG.search(text):
            return 1, ("El Torito catalogue found but it lists no boot image at all — "
                       "this ISO boots neither BIOS nor UEFI firmware")
        return 3, ("UNVERIFIED: no El Torito catalogue in the report — xorriso missing, "
                   "or it wrote something this parser does not understand")
    uefi = sorted(n for n, platform in images.items() if platform == "UEFI")
    bios = sorted(n for n, platform in images.items() if platform in ("BIOS", "X86"))
    listed = ", ".join(f"#{n} {platform} {paths.get(n, '(path not reported)')}"
                       for n, platform in sorted(images.items()))
    if not uefi:
        return 1, (f"no UEFI boot image in the El Torito catalogue — this ISO cannot boot UEFI "
                   f"firmware, which is every machine we target. Images found: {listed}")
    head = f"UEFI boot image present: #{uefi[0]} {paths.get(uefi[0], '(path not reported)')}"
    if not bios:
        return 0, (f"{head}; no BIOS/legacy boot image, so this image is UEFI-only "
                   f"(fine for `modern`, it will not boot the `legacy` profile)")
    return 0, f"{head}; BIOS boot image also present: #{bios[0]} {paths.get(bios[0], '')}".rstrip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--el-torito-report", required=True, type=Path,
                        help="file holding `xorriso -indev <iso> -report_el_torito plain` output")
    args = parser.parse_args(argv)
    try:
        report = args.el_torito_report.read_text(errors="replace")
    except OSError as exc:
        print(f"UNVERIFIED: cannot read {args.el_torito_report}: {exc}")
        return 3
    code, message = el_torito_verdict(report)
    prefix = {0: "OK", 1: "FAIL", 3: "UNVERIFIED"}[code]
    print(f"{prefix}: {message}")
    return code


if __name__ == "__main__":
    sys.exit(main())
