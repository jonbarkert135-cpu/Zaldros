# SPDX-License-Identifier: GPL-3.0-or-later
"""The native ISO push filter must cover actual recipe and resource inputs."""
import importlib.util
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT / ".github/workflows/iso.yml"


def push_patterns():
    # The workflow uses a JSON-compatible flow list for this data. Keep stdlib
    # parsing and simple literal-directory /** filters; do not emulate YAML/globs.
    match = re.search(r"(?m)^    paths: (\[.*\])$", WORKFLOW.read_text())
    assert match, "keep the ISO push paths as a JSON-compatible flow list"
    patterns = json.loads(match[1])
    assert patterns and all(isinstance(p, str) for p in patterns)
    assert all(not re.search(r"[!*?\[\]]", p.removesuffix("/**")) for p in patterns), (
        "coverage model supports literal paths and literal-directory /** only")
    return patterns


def selected(path):
    return any(path.startswith(p[:-2]) if p.endswith("/**") else path == p
               for p in push_patterns())


def files_under(path):
    assert path.exists(), f"recipe input is missing: {path}"
    return [path] if path.is_file() else [p for p in path.rglob("*") if p.is_file()
        and not {"__pycache__", ".pytest_cache"}.intersection(p.parts)
        and p.suffix not in {".pyc", ".pyo"}]


def consumed_inputs(group):
    if group == "recipe":
        recipe = (ROOT / "build/iso/build-iso.sh").read_text()
        references = set(re.findall(r"\$REPO/([A-Za-z0-9_./-]+)", recipe))
        assert references, "no recipe inputs found"
        return [p for ref in references for p in files_under(ROOT / ref)]
    if group == "assets":
        spec = importlib.util.spec_from_file_location("stage_assets", ROOT / "build/iso/stage-assets.py")
        stage = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(stage)
        inventory = json.loads(stage.MANIFEST.read_text())
        # Validation hashes even excluded references/generators before staging.
        return [stage.MANIFEST] + [ROOT / e["path"] for e in inventory["files"]]
    # App code is a planned integration input even before all Office frontends
    # are installed in the ISO. Selecting it does not claim they are packaged.
    return files_under(ROOT / "apps")


@pytest.mark.parametrize("group", ["recipe", "assets", "apps"])
def test_push_filter_covers_actual_inputs(group):
    inputs = consumed_inputs(group)
    assert inputs
    missing = sorted(p.relative_to(ROOT).as_posix() for p in inputs
                     if not selected(p.relative_to(ROOT).as_posix()))
    assert not missing, f"ISO push filter omits {group} inputs: {missing[:10]}"


@pytest.mark.parametrize("path", ["README.md", "docs/office/BUILD.md", "docs/ci/iso.yml",
                                  "build/Containerfile.base", "build/Containerfile.desktop"])
def test_docs_and_historical_container_changes_do_not_rebuild_the_iso(path):
    assert not selected(path)


def test_workflow_changes_retest_the_workflow_and_reference_copy_matches():
    assert selected(WORKFLOW.relative_to(ROOT).as_posix())
    assert WORKFLOW.read_bytes() == (ROOT / "docs/ci/iso.yml").read_bytes()
