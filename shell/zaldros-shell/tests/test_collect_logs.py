"""`tools/collect-logs.sh` is the only debugging channel we have to real hardware.

It runs on a machine nobody can look at, once, possibly from a live USB, and whatever it fails to
collect is a round trip of "please run this again". So it is tested the only way that means
anything: it is actually executed here — on a host with no systemd, no D-Bus, no PCI bus and no
screen — and it still has to exit 0 and produce a readable archive.
"""

import os
import shutil
import subprocess
import tarfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "tools" / "collect-logs.sh"


@pytest.fixture(scope="module")
def archive(tmp_path_factory):
    out = tmp_path_factory.mktemp("collected")
    env = dict(os.environ, PYTHONPATH=str(REPO / "backend"))
    done = subprocess.run(["sh", str(SCRIPT), str(out)], capture_output=True, text=True,
                          env=env, timeout=300)
    assert done.returncode == 0, done.stderr
    archives = list(out.glob("zaldros-logs-*.tar.gz"))
    assert len(archives) == 1, done.stdout
    assert str(archives[0]) in done.stdout, "the path must be printed, it is what the user sends"
    return archives[0]


def test_the_archive_holds_every_section_even_where_the_tool_is_missing(archive):
    with tarfile.open(archive) as tar:
        names = {Path(name).name for name in tar.getnames()}
        root = tar.getnames()[0].split("/")[0]
        summary = tar.extractfile(f"{root}/00-summary.txt").read().decode()
        failed = tar.extractfile(f"{root}/14-systemd-failed.txt").read().decode()
    for expected in ("00-summary.txt", "10-journal-boot.log", "13-dmesg.log",
                     "14-systemd-failed.txt", "35-backend-status.json", "40-cpuinfo.txt",
                     "45-network.txt", "48-firmware.txt"):
        assert expected in names, expected
    assert "kernel: Linux" in summary
    # A missing tool is a recorded fact, not a silently empty file.
    assert failed.strip(), "an empty probe file tells the reader nothing"


def test_the_backend_answers_even_with_no_buses(archive):
    """The point of the file: which facet failed and what it said, straight from the machine."""
    with tarfile.open(archive) as tar:
        root = tar.getnames()[0].split("/")[0]
        status = tar.extractfile(f"{root}/35-backend-status.json").read().decode()
    assert '"tray"' in status and '"battery"' in status
    assert "system_bus_error" in status, "why the bus is unreachable is the interesting part"


def test_it_collects_no_secrets():
    """Someone will send this archive over Slack. It must be safe to send."""
    text = SCRIPT.read_text()
    for forbidden in ("--show-secrets", "/etc/shadow", "/etc/NetworkManager/system-connections",
                      "id_rsa", ".ssh"):
        assert forbidden not in text, forbidden


def test_it_ships_inside_the_image():
    """A checkout is exactly what a machine booted from the USB stick does not have."""
    build = (REPO / "build" / "iso" / "build-iso.sh").read_text()
    assert "collect-logs.sh" in build and "zaldros-collect-logs" in build
    assert "zaldros-collect-logs" in (REPO / "INSTALL.md").read_text()


def test_it_is_executable_and_shell_clean():
    assert os.access(SCRIPT, os.X_OK), "a live-USB user should not have to chmod it"
    if shutil.which("sh"):
        check = subprocess.run(["sh", "-n", str(SCRIPT)], capture_output=True, text=True)
        assert check.returncode == 0, check.stderr
