"""A build that fails must leave the diagnostics it promises — including the last half of the run.

`build-iso.sh` says its debug directory is written "whether it succeeds or fails", but it disarmed
its own EXIT trap right before `mksquashfs` and `grub-mkrescue`. Consequences, both seen in real
runs: the squashfs/ISO half of the build produced no diagnostics at all, and on every *successful*
build `environment.txt` was simply absent — so the CI step that pastes it into the run summary died
with exit 1 behind `continue-on-error`, taking the last 200 lines of the build log with it. That is
the file you read first when a build breaks, and it was silently gone.

The behavioural half of this file runs the real script as a non-root user: it stops early by
design, and the diagnostics still have to be there.
"""

import os
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "build" / "iso" / "build-iso.sh"


def test_the_exit_trap_is_never_disarmed_before_the_end():
    lines = SCRIPT.read_text().splitlines()
    armed = [i for i, line in enumerate(lines) if line.strip().startswith("trap collect_debug")]
    assert armed, "the diagnostics trap must exist"
    disarms = [i for i, line in enumerate(lines) if "trap - EXIT" in line]
    assert not disarms, (
        "disarming the trap mid-script is exactly how the squashfs and ISO steps lost their "
        f"diagnostics (found at lines {[i + 1 for i in disarms]})")


def test_collect_debug_cannot_be_cut_short_by_a_failing_probe():
    body = SCRIPT.read_text().split("collect_debug() {", 1)[1].split("\ntrap ", 1)[0]
    assert "set +e" in body, (
        "under `set -e` the first failing probe aborts the whole group and environment.txt is "
        "written half-finished, which reads as complete")


@pytest.mark.skipif(os.geteuid() == 0, reason="running the real build as root would start a build")
def test_a_failed_build_still_writes_its_diagnostics(tmp_path):
    debug = tmp_path / "build-debug-full"
    # No network in the assertion path: an unreachable base tarball makes the script stop in its
    # first real step, which is all this test needs. The point is what it leaves behind.
    env = dict(os.environ, DEBUG_DIR=str(debug), WORK=str(tmp_path / "work"),
               BASE_TARBALL="file:///nonexistent-zaldros-base.tar.gz")
    done = subprocess.run(["bash", str(SCRIPT), "full", str(tmp_path / "out.iso")],
                          capture_output=True, text=True, env=env, cwd=tmp_path, timeout=600)
    assert done.returncode != 0, "without root this build cannot succeed; if it did, read the log"
    assert "diagnostics written to" in done.stdout + done.stderr

    environment = debug / "environment.txt"
    assert environment.is_file(), "the file the CI summary step reads was not written"
    text = environment.read_text()
    # Every section header has to be present: a diagnostic that stops at the first failing probe
    # is the defect this test exists for.
    for section in ("=== exit code:", "=== uname -a", "=== df -h", "=== free -h",
                    "=== rootfs:", "=== step exit codes"):
        assert section in text, f"{section} missing — collect_debug stopped early"
    assert (debug / "steps.tsv").is_file()
