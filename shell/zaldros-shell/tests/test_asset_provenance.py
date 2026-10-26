# SPDX-License-Identifier: GPL-3.0-or-later
"""Shipping policy uses hashes and an explicit list, not an unrestricted assets copy."""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("asset_staging", REPO / "build/iso/stage-assets.py")
assets = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assets)


def test_repository_inventory_matches_and_staging_excludes_references(tmp_path):
    entries = assets.inventory(REPO, assets.MANIFEST)
    destination = tmp_path / "shipped"
    count = assets.stage(REPO, assets.MANIFEST, destination)
    assert count == sum(entry["shipped"] for entry in entries)
    assert not (destination / "refs").exists()
    assert not (destination / "wallpaper/generate.py").exists()
    assert (destination / "fonts/pt-sans/LICENSE.txt").is_file()
    assert (destination / "icons/fluent/LICENSE").is_file()
    assert (destination / "PROVENANCE.json").is_file()
    assert (destination / "wallpaper/zaldros-default.png").is_file()


@pytest.fixture
def inventory(tmp_path):
    repo = tmp_path / "repo"
    path = repo / "assets/icons/a.svg"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"original")
    entry = dict(path="assets/icons/a.svg", component="test", shipped=True,
                 sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(dict(components={"test": {}}, files=[entry])))
    return repo, path, manifest


@pytest.mark.parametrize("failure", ["tamper", "unknown", "symlink", "traversal", "duplicate"])
def test_unreviewed_asset_cannot_be_staged(inventory, tmp_path, failure):
    repo, path, manifest = inventory
    if failure == "tamper":
        path.write_bytes(b"altered")
    elif failure == "unknown":
        (path.parent / "new.svg").write_bytes(b"unreviewed")
    elif failure == "symlink":
        path.unlink()
        path.symlink_to(manifest)
    else:
        data = json.loads(manifest.read_text())
        if failure == "traversal":
            data["files"][0]["path"] = "assets/../outside"
        else:
            data["files"].append(data["files"][0])
        manifest.write_text(json.dumps(data))
    dest = tmp_path / "output"
    with pytest.raises(ValueError):
        assets.stage(repo, manifest, dest)
    assert not dest.exists()


def test_staging_preserves_existing_destination(inventory, tmp_path):
    repo, _, manifest = inventory
    dest = tmp_path / "output"
    dest.mkdir()
    (dest / "keep").write_text("original")
    with pytest.raises(ValueError, match="overwrite"):
        assets.stage(repo, manifest, dest)
    assert (dest / "keep").read_text() == "original"
