#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Validate the asset inventory and stage only explicitly selected entries.

The inventory records known provenance gaps, not a legal clearance certificate.
Research references and generators never enter the image. New assets require review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path, PurePosixPath

REPO = Path(__file__).resolve().parents[2]
MANIFEST = REPO / "build" / "provenance" / "assets.json"


def inventory(repo: Path, manifest: Path) -> list[dict]:
    data = json.loads(manifest.read_text())
    entries = data["files"]
    paths = set()
    for entry in entries:
        relative = PurePosixPath(entry["path"])
        if (relative.is_absolute() or ".." in relative.parts or relative.parts[0] != "assets"
                or str(relative) in paths):
            raise ValueError(f"invalid/duplicate inventory path: {relative}")
        paths.add(str(relative))
        if entry["component"] not in data["components"]:
            raise ValueError(f"unknown component: {relative}")
        if not isinstance(entry["shipped"], bool):
            raise ValueError(f"missing explicit shipping decision: {relative}")
        if entry["shipped"] and ("refs" in relative.parts or relative.suffix == ".py"):
            raise ValueError(f"research/generator cannot be shipped: {relative}")
        source = repo / str(relative)
        if source.is_symlink() or not source.is_file():
            raise ValueError(f"missing or symlink asset: {relative}")
        if hashlib.sha256(source.read_bytes()).hexdigest() != entry["sha256"]:
            raise ValueError(f"asset hash mismatch: {relative}")
    actual = set()
    for path in (repo / "assets").rglob("*"):
        relative = path.relative_to(repo).as_posix()
        if "__pycache__" in path.parts or (relative.startswith("assets/refs/") and "/cache/" in relative):
            continue
        if path.is_symlink():
            raise ValueError(f"symlink asset: {relative}")
        if path.is_file():
            actual.add(relative)
    if actual != paths:
        raise ValueError(f"asset inventory out of date: added={sorted(actual - paths)}, removed={sorted(paths - actual)}")
    return entries


def stage(repo: Path, manifest: Path, destination: Path) -> int:
    entries = inventory(repo, manifest)
    if destination.exists() or destination.is_symlink():
        raise ValueError("asset destination must not exist; refusing to overwrite")
    if destination.resolve().is_relative_to(repo.resolve() / "assets"):
        raise ValueError("cannot stage inside source assets")
    destination.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with tempfile.TemporaryDirectory(prefix=".assets-", dir=destination.parent) as temporary:
        tree = Path(temporary) / "assets"
        tree.mkdir()
        for entry in entries:
            if not entry["shipped"]:
                continue
            relative = Path(entry["path"]).relative_to("assets")
            target = tree / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(repo / entry["path"], target)
            count += 1
        shutil.copyfile(manifest, tree / "PROVENANCE.json")
        tree.replace(destination)
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", type=Path, help="new image asset directory; omit to check inventory only")
    args = parser.parse_args()
    try:
        if args.dest:
            print(f"staged {stage(REPO, MANIFEST, args.dest)} assets plus provenance manifest")
        else:
            print(f"verified {len(inventory(REPO, MANIFEST))} asset records")
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(1, f"asset inventory failed: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
