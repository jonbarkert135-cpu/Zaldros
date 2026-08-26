"""Guard: the shell must start from *the files the ISO actually installs*, not from the repo.

Two production outages came from this gap, both invisible to every other test because the tests
import the shell out of the repository checkout:

* run #19 — `assets/` resolved to `/assets` in the flat /opt/zaldros layout: no wallpaper, no font,
  no icons.
* run #24 — `data/` was never copied into the image at all, so the shell died at startup with
  FileNotFoundError on `/opt/zaldros/data/pinned.json` and all nine variant x profile combinations
  booted to a black screen while CI stayed green.

This test reads the copy commands out of `build/iso/build-iso.sh`, builds the same flat tree in a
temporary directory, and renders one frame from it in a subprocess. Forgetting a directory in the
build script fails here instead of in a 13-minute ISO run.
"""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("PySide6")

REPO = Path(__file__).resolve().parents[3]
BUILD = REPO / "build" / "iso" / "build-iso.sh"
TARGET = "$ROOT/opt/zaldros"


def iso_copies() -> list[tuple[Path, str]]:
    """(source, destination name) pairs that build-iso.sh copies into /opt/zaldros."""
    script = BUILD.read_text()
    # Join continuation lines so a wrapped `cp -a ... \` command is parsed as one command.
    script = script.replace("\\\n", " ")
    pairs: list[tuple[Path, str]] = []
    for line in script.splitlines():
        line = line.strip()
        if not line.startswith("cp ") or TARGET not in line:
            continue
        words = [w for w in shlex.split(line) if w not in {"cp", "-a"}]
        destination, sources = words[-1], words[:-1]
        for source in sources:
            if not source.startswith("$REPO/"):
                continue
            path = REPO / source[len("$REPO/") :]
            name = destination[len(TARGET) :].strip("/") or path.name
            pairs.append((path, name))
    return pairs


def test_build_script_copies_are_readable() -> None:
    copies = iso_copies()
    assert copies, "no cp commands into /opt/zaldros found in build-iso.sh"
    missing = [str(source) for source, _ in copies if not source.exists()]
    assert not missing, f"build-iso.sh copies paths that do not exist: {missing}"


def test_shell_renders_from_the_flat_iso_layout(tmp_path: Path) -> None:
    """Stage /opt/zaldros as the ISO builds it, then render a frame with only that tree present."""
    root = tmp_path / "opt-zaldros"
    root.mkdir()
    for source, name in iso_copies():
        subprocess.run(["cp", "-a", str(source), str(root / name)], check=True)

    output = tmp_path / "flat.png"
    env = {
        **os.environ,
        "PYTHONPATH": str(root),
        "QT_QPA_PLATFORM": "offscreen",
        # No repo paths and no override may leak in: the image has neither.
        "ZALDROS_ASSETS": "",
        "ZALDROS_DATA": "",
    }
    env.pop("ZALDROS_ASSETS")
    env.pop("ZALDROS_DATA")
    result = subprocess.run(
        [sys.executable, "-m", "zaldros_shell", "render", "--out", str(output)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"shell failed to start from the ISO layout:\n{result.stderr}"
    assert output.is_file() and output.stat().st_size > 10_000, "flat-layout render produced no frame"


def test_flat_layout_uses_the_installed_assets_and_data(tmp_path: Path) -> None:
    """The staged tree must carry the wallpaper and the pinned list, not fall back to the repo."""
    root = tmp_path / "opt-zaldros"
    root.mkdir()
    for source, name in iso_copies():
        subprocess.run(["cp", "-a", str(source), str(root / name)], check=True)
    assert (root / "assets" / "wallpaper").is_dir(), "the ISO ships no wallpaper directory"
    assert (root / "data" / "pinned.json").is_file(), "the ISO ships no data/pinned.json"
