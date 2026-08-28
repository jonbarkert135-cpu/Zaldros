"""The evidence channel has to survive two CI runs pushing at the same moment.

`iso` run 33161289986 went red with every build and every boot job passing: two overlapping runs
force-pushed the same `ci-logs-boot-services-mid` branch and GitHub rejected the loser with
`cannot lock ref … is at X but expected Y`. A lost ref race says nothing about Zaldros, so the
publisher retries — but a push that keeps failing still has to be reported and still has to exit
non-zero, or we are back to a green job that published nothing.

Tested against a real local bare repository, and against a stub `git` that loses the race twice
before letting the real one through.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "build" / "iso" / "publish-evidence.sh"
GIT = shutil.which("git")

pytestmark = pytest.mark.skipif(GIT is None, reason="git is not installed on this host")


def _run(directory, branch, label, remote, extra_path=None, attempts=None):
    env = dict(os.environ, EVIDENCE_REMOTE=str(remote), EVIDENCE_SLEEP="0")
    if attempts:
        env["EVIDENCE_ATTEMPTS"] = attempts
    if extra_path:
        env["PATH"] = f"{extra_path}:{env['PATH']}"
    return subprocess.run(["sh", str(SCRIPT), str(directory), branch, label],
                          capture_output=True, text=True, env=env, timeout=180)


def _bare(tmp_path):
    remote = tmp_path / "remote.git"
    subprocess.run([GIT, "init", "-q", "--bare", str(remote)], check=True)
    return remote


def _files_on(remote, branch):
    listing = subprocess.run([GIT, "--git-dir", str(remote), "ls-tree", "-r", "--name-only", branch],
                             capture_output=True, text=True, check=True)
    return set(listing.stdout.split())


def test_the_evidence_lands_on_its_own_branch(tmp_path):
    results = tmp_path / "results"
    results.mkdir()
    (results / "zaldros-full-modern.json").write_text('{"boot": "ok"}')
    (results / "serial.log").write_text("GRUB: booting\n")
    remote = _bare(tmp_path)

    done = _run(results, "ci-logs-boot-full-modern", "boot full/modern — success", remote)
    assert done.returncode == 0, done.stdout + done.stderr
    files = _files_on(remote, "ci-logs-boot-full-modern")
    assert {"zaldros-full-modern.json", "serial.log", "RUN.txt"} <= files
    assert "attempt 1/5" in done.stdout


def test_a_job_that_produced_nothing_still_says_so_on_its_branch(tmp_path):
    remote = _bare(tmp_path)
    done = _run(tmp_path / "never-written", "ci-logs-full", "diagnostics: run 1 full failure", remote)
    assert done.returncode == 0, done.stdout + done.stderr
    files = _files_on(remote, "ci-logs-full")
    assert "NOTE.txt" in files and "RUN.txt" in files
    shown = subprocess.run([GIT, "--git-dir", str(remote), "show", "ci-logs-full:RUN.txt"],
                           capture_output=True, text=True, check=True)
    assert "failure" in shown.stdout


def _stub_git_that_loses_the_race(tmp_path, failures):
    """A `git` on PATH whose first `push` calls fail exactly the way GitHub rejects a lost race."""
    stub_dir = tmp_path / "stub"
    stub_dir.mkdir()
    counter = tmp_path / "push-count"
    counter.write_text("0")
    (stub_dir / "git").write_text(f"""#!/bin/sh
for arg in "$@"; do
  if [ "$arg" = "push" ]; then
    n=$(cat {counter}); n=$((n + 1)); echo "$n" > {counter}
    if [ "$n" -le {failures} ]; then
      echo "To https://x-access-token:ghs_SECRETTOKEN@github.com/owner/repo" >&2
      echo " ! [remote rejected] branch -> branch (cannot lock ref: is at aaa but expected bbb)" >&2
      exit 1
    fi
  fi
done
exec {GIT} "$@"
""")
    (stub_dir / "git").chmod(0o755)
    return stub_dir, counter


def test_a_lost_ref_race_is_retried_until_it_lands(tmp_path):
    results = tmp_path / "results"
    results.mkdir()
    (results / "frame.json").write_text("{}")
    remote = _bare(tmp_path)
    stub_dir, counter = _stub_git_that_loses_the_race(tmp_path, failures=2)

    done = _run(results, "ci-logs-boot-services-mid", "boot services/mid — success", remote,
                extra_path=stub_dir)
    assert done.returncode == 0, done.stdout + done.stderr
    assert counter.read_text().strip() == "3", "it must have taken three pushes"
    assert "attempt 1/5 to publish" in done.stdout and "cannot lock ref" in done.stdout
    assert "frame.json" in _files_on(remote, "ci-logs-boot-services-mid")


def test_a_push_that_never_lands_fails_loudly_and_never_leaks_the_token(tmp_path):
    results = tmp_path / "results"
    results.mkdir()
    (results / "frame.json").write_text("{}")
    remote = _bare(tmp_path)
    stub_dir, counter = _stub_git_that_loses_the_race(tmp_path, failures=99)

    done = _run(results, "ci-logs-full", "diagnostics", remote, extra_path=stub_dir, attempts="3")
    assert done.returncode == 1, "a channel that published nothing is not a success"
    assert counter.read_text().strip() == "3"
    assert "after 3 attempts" in done.stdout
    assert "ghs_SECRETTOKEN" not in done.stdout + done.stderr, "the token must be scrubbed"
    assert "https://github.com/owner/repo" in done.stdout, "the scrubbed URL still has to be useful"


def test_ppm_screendumps_are_converted_so_a_browser_can_show_them(tmp_path):
    if shutil.which("mogrify") is None:
        pytest.skip("imagemagick is not installed here; CI installs it in the boot job")
    results = tmp_path / "results"
    results.mkdir()
    (results / "shot.ppm").write_bytes(b"P6\n1 1\n255\n" + bytes([1, 2, 3]))
    remote = _bare(tmp_path)
    done = _run(results, "ci-logs-boot-full-low", "boot full/low — success", remote)
    assert done.returncode == 0, done.stdout + done.stderr
    files = _files_on(remote, "ci-logs-boot-full-low")
    assert "shot.png" in files and "shot.ppm" not in files


def test_the_workflow_mirror_uses_the_publisher_for_every_evidence_branch():
    workflow = (REPO / "docs" / "ci" / "iso.yml").read_text()
    assert workflow.count("publish-evidence.sh") == 2, \
        "both the build and the boot job publish through the retrying script"
    assert "git push -qf" not in workflow, "no hand-rolled push left to lose a race"
