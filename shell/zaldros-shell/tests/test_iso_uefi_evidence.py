"""The UEFI half of a built ISO must be proven from the El Torito catalogue, not guessed.

Every green build so far ended its log with

    xorriso : FAILURE : Cannot find path '/EFI' in loaded ISO image
    xorriso : aborting : -abort_on 'FAILURE' encountered 'FAILURE'

because the probe looked for a /EFI directory that grub-mkrescue never creates. The real evidence
is three lines higher in the same report and was never read. The fixture below is the verbatim
report from iso run 33161289986, build (full).
"""

import importlib.util
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
ISO = REPO / "build" / "iso"

REAL_REPORT = """xorriso 1.5.6 : RockRidge filesystem manipulator, libburnia project.

xorriso : NOTE : Loading ISO image tree from LBA 0
xorriso : UPDATE :     594 nodes read in 1 seconds
xorriso : NOTE : Detected El-Torito boot information which currently is set to be discarded
Drive current: -indev 'zaldros-full.iso'
Media current: stdio file, overwriteable
Media status : is written , is appendable
Boot record  : El Torito , MBR protective-msdos-label grub2-mbr cyl-align-off GPT APM
Media summary: 1 session, 1489500 data blocks, 2909m data, 76.4g free
Volume id    : 'ZALDROS'
El Torito catalog  : 1615  1
El Torito cat path : /boot.catalog
El Torito images   :   N  Pltf  B   Emul  Ld_seg  Hdpt  Ldsiz         LBA
El Torito boot img :   1  BIOS  y   none  0x0000  0x00      4        2977
El Torito boot img :   2  UEFI  y   none  0x0000  0x00   5760          72
El Torito img path :   1  /boot/grub/i386-pc/eltorito.img
El Torito img opts :   1  boot-info-table grub2-boot-info
El Torito img path :   2  /efi.img
"""


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ISO / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


verify = _load("verify-iso")


def test_the_iso_we_actually_build_is_proven_to_be_uefi_bootable():
    code, message = verify.el_torito_verdict(REAL_REPORT)
    assert code == 0, message
    assert "/efi.img" in message, message
    assert "eltorito.img" in message, "the BIOS image is evidence too, and belongs in the line"


def test_an_iso_with_no_uefi_image_fails_instead_of_shipping():
    bios_only = REAL_REPORT.replace(
        "El Torito boot img :   2  UEFI  y   none  0x0000  0x00   5760          72\n", "")
    code, message = verify.el_torito_verdict(bios_only)
    assert code == 1
    assert "cannot boot UEFI" in message


def test_a_catalogue_with_no_images_is_a_failure_not_a_shrug():
    empty = "\n".join(line for line in REAL_REPORT.splitlines()
                      if not line.startswith("El Torito boot img")
                      and not line.startswith("El Torito img path"))
    code, message = verify.el_torito_verdict(empty)
    assert code == 1
    assert "no boot image" in message


def test_a_report_that_could_not_be_produced_is_unverified_never_a_pass():
    for text in ("", "xorriso: command not found", "some unrelated output\n"):
        code, message = verify.el_torito_verdict(text)
        assert code == 3, text
        assert "UNVERIFIED" in message


def test_a_uefi_only_image_passes_but_says_it_will_not_boot_legacy():
    uefi_only = REAL_REPORT.replace(
        "El Torito boot img :   1  BIOS  y   none  0x0000  0x00      4        2977\n", "")
    code, message = verify.el_torito_verdict(uefi_only)
    assert code == 0
    assert "UEFI-only" in message and "legacy" in message


def test_the_exit_codes_are_the_contract_the_build_script_relies_on(tmp_path):
    report = tmp_path / "el-torito.txt"
    report.write_text(REAL_REPORT)
    done = subprocess.run([sys.executable, str(ISO / "verify-iso.py"),
                           "--el-torito-report", str(report)], capture_output=True, text=True)
    assert done.returncode == 0
    assert done.stdout.startswith("OK: ")

    report.write_text("")
    done = subprocess.run([sys.executable, str(ISO / "verify-iso.py"),
                           "--el-torito-report", str(report)], capture_output=True, text=True)
    assert done.returncode == 3
    assert done.stdout.startswith("UNVERIFIED: ")

    done = subprocess.run([sys.executable, str(ISO / "verify-iso.py"),
                           "--el-torito-report", str(tmp_path / "nope.txt")],
                          capture_output=True, text=True)
    assert done.returncode == 3, "an unreadable report is unverified, not a pass"


def test_the_build_script_acts_on_those_codes_and_no_longer_probes_a_slash_efi_tree():
    script = (ISO / "build-iso.sh").read_text()
    code = "\n".join(line for line in script.splitlines() if not line.lstrip().startswith("#"))
    assert "-find /EFI" not in code, "the probe that printed FAILURE on every good build"
    assert "verify-iso.py" in script and "--el-torito-report" in script
    assert '[ "$et_rc" -ne 1 ] || exit 1' in script, "rc 1 must stop the build"
