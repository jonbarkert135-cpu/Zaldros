#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Download rootfs, authenticate Ubuntu's checksum manifest, hash, then extract.

No extraction or fallback occurs on download, signature or checksum failure.
The checked-in policy pins the signing authority, independently of the fetched key.
Requires curl, gpg and tar; never reads the user's GnuPG configuration or keyring.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import unquote, urlsplit

POLICY = Path(__file__).with_name("ubuntu-cdimage-policy.json")


def download(url: str, destination: Path) -> None:
    parts = urlsplit(url)
    if (parts.scheme != "https" or not parts.hostname or parts.username or parts.password
            or parts.fragment):
        raise ValueError("rootfs downloads require HTTPS without URL credentials/fragments")
    subprocess.run(["curl", "--fail", "--silent", "--show-error", "--location",
                    "--proto", "=https", "--proto-redir", "=https",
                    "--connect-timeout", "20", "--max-time", "600",
                    "--output", str(destination), url], check=True)


def verify_signature(manifest: Path, signature: Path, keyring: Path,
                     fingerprints: list[str], homedir: Path) -> None:
    homedir.mkdir(mode=0o700, exist_ok=True)
    result = subprocess.run(
        ["gpg", "--no-options", "--homedir", str(homedir), "--batch",
         "--no-auto-key-retrieve", "--no-default-keyring", "--keyring", str(keyring.resolve()),
         "--status-fd", "1", "--verify", str(signature), str(manifest)],
        check=True, capture_output=True, text=True)
    trusted = {fp.upper() for fp in fingerprints}
    for line in result.stdout.splitlines():
        fields = line.split()
        # VALIDSIG includes a signing subkey and (for OpenPGP) primary fingerprint.
        if len(fields) >= 11 and fields[:2] == ["[GNUPG:]", "VALIDSIG"]:
            if fields[2].upper() in trusted or fields[-1].upper() in trusted:
                return
    raise ValueError("checksum manifest is not signed by the pinned Ubuntu CD-image key")


def verify_digest(archive: Path, manifest: Path, filename: str) -> str:
    matches = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        entry = re.fullmatch(r"([0-9a-fA-F]{64}) [ *](.+)", line)
        if entry and entry[2] == filename:
            matches.append(entry[1].lower())
    if len(matches) != 1:
        raise ValueError("signed manifest must contain exactly one entry for the rootfs filename")
    with archive.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest != matches[0]:
        raise ValueError("rootfs SHA256 mismatch; refusing extraction")
    return digest


def fetch(url: str, root: Path, evidence: Path, keyring: Path | None = None) -> None:
    # Reject URLs whose query changes the artifact identity/manifest directory.
    parts = urlsplit(url)
    filename = unquote(parts.path.rsplit("/", 1)[-1])
    if parts.query or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*\.tar\.gz", filename):
        raise ValueError("rootfs URL must name a .tar.gz artifact without a query")
    if root.is_symlink() or (root.exists() and (not root.is_dir() or any(root.iterdir()))):
        raise ValueError("rootfs destination must be an empty directory, not a symlink")
    policy = json.loads(POLICY.read_text())
    fingerprints = policy["primary_fingerprints"]
    if not fingerprints or any(not re.fullmatch(r"[0-9A-F]{40}", fp) for fp in fingerprints):
        raise ValueError("invalid checked-in signing-key policy")
    evidence.mkdir(parents=True, exist_ok=True)
    # A failed refresh must not leave a previous success record looking current.
    receipt = evidence / "rootfs-verification.json"
    receipt.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix="zaldros-rootfs-") as work:
        directory = Path(work)
        archive = directory / filename
        manifest = directory / "SHA256SUMS"
        signature = directory / "SHA256SUMS.gpg"
        base = url.rsplit("/", 1)[0]
        download(base + "/SHA256SUMS", manifest)
        download(base + "/SHA256SUMS.gpg", signature)
        if keyring is None:
            keyring = directory / "signer.asc"
            download(policy["key_url"], keyring)
            # Dearmor into an isolated keyring: the downloaded key is NOT trusted until
            # verification produces a VALIDSIG matching the independent fingerprint policy.
            binary_keyring = directory / "signer.gpg"
            (directory / "gnupg").mkdir(mode=0o700)
            subprocess.run(["gpg", "--no-options", "--homedir", str(directory / "gnupg"), "--batch", "--dearmor",
                            "--output", str(binary_keyring), str(keyring)], check=True)
            keyring = binary_keyring
        verify_signature(manifest, signature, keyring, fingerprints, directory / "gnupg")
        download(url, archive)
        digest = verify_digest(archive, manifest, filename)
        # Stage the tree. Even tar failure cannot leave a partially populated rootfs.
        root.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".verified-rootfs-", dir=root.parent) as stage:
            tree = Path(stage) / "tree"
            tree.mkdir()
            subprocess.run(["tar", "--extract", "--gzip", "--file", str(archive),
                            "--directory", str(tree)], check=True)
            tree.replace(root)
        for source in (manifest, signature):
            (evidence / source.name).write_bytes(source.read_bytes())
        receipt.write_text(json.dumps({"url": url, "sha256": digest,
                                      "trusted_primary_fingerprints": fingerprints,
                                      "status": "verified-and-extracted"}, indent=2) + "\n")
    print(f"rootfs authenticated and extracted: {filename} sha256={digest}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--keyring", type=Path, help="optional local keyring; signer is still pinned")
    args = parser.parse_args()
    try:
        fetch(args.url, args.root, args.evidence, args.keyring)
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        parser.exit(1, f"rootfs authentication/extraction failed: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
