# SPDX-License-Identifier: GPL-3.0-or-later
"""Real OpenPGP verification and tamper failures, without network or root."""
import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import tarfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("rootfs_fetch", REPO / "build/iso/fetch-rootfs.py")
rootfs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rootfs)


@pytest.fixture(scope="module")
def signer(tmp_path_factory):
    # Deliberately not skipped: the build-authentication gate requires working GnuPG.
    directory = tmp_path_factory.mktemp("test-rootfs-signer")
    home = directory / "gnupg"
    home.mkdir(mode=0o700)
    command = ["gpg", "--no-options", "--homedir", str(home), "--batch",
               "--pinentry-mode", "loopback", "--passphrase", ""]
    try:
        subprocess.run(command + ["--quick-generate-key", "Zaldros test fixture <fixture@invalid>",
                                  "ed25519", "sign", "0"], check=True, capture_output=True)
        output = subprocess.check_output(command + ["--with-colons", "--list-keys"], text=True)
        fingerprint = next(line.split(":")[9] for line in output.splitlines() if line.startswith("fpr:"))
        keyring = directory / "signer.gpg"
        keyring.write_bytes(subprocess.check_output(command + ["--export", fingerprint]))
        yield command, fingerprint, keyring
    finally:
        subprocess.run(["gpgconf", "--homedir", str(home), "--kill", "gpg-agent"], check=False)


@pytest.fixture
def release(tmp_path, signer, monkeypatch):
    command, fingerprint, keyring = signer
    archive = tmp_path / "ubuntu-base-test-amd64.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        member = tarfile.TarInfo("etc/os-release")
        content = b"ID=ubuntu\n"
        member.size = len(content)
        tar.addfile(member, io.BytesIO(content))
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    manifest = tmp_path / "SHA256SUMS"
    signature = tmp_path / "SHA256SUMS.gpg"
    policy = tmp_path / "policy.json"
    policy.write_text(json.dumps({"primary_fingerprints": [fingerprint], "key_url": "unused"}))
    monkeypatch.setattr(rootfs, "POLICY", policy)

    def sign(text):
        manifest.write_text(text)
        subprocess.run(command + ["--yes", "--output", str(signature), "--detach-sign", str(manifest)],
                       check=True, capture_output=True)

    sign(f"{digest} *{archive.name}\n")

    def download(url, destination):
        shutil.copyfile(tmp_path / url.rsplit("/", 1)[-1], destination)

    monkeypatch.setattr(rootfs, "download", download)
    return archive, manifest, signature, policy, keyring, sign


def test_verified_release_extracts_and_keeps_receipt(tmp_path, release):
    archive, _, _, _, keyring, _ = release
    root = tmp_path / "root"
    evidence = tmp_path / "evidence"
    rootfs.fetch(f"https://release.invalid/{archive.name}", root, evidence, keyring)
    assert (root / "etc/os-release").read_text() == "ID=ubuntu\n"
    receipt = json.loads((evidence / "rootfs-verification.json").read_text())
    assert receipt["sha256"] == hashlib.sha256(archive.read_bytes()).hexdigest()
    assert receipt["status"] == "verified-and-extracted"
    assert (evidence / "SHA256SUMS.gpg").is_file()


def test_fetched_public_key_still_needs_the_independent_policy(tmp_path, release, signer):
    archive, _, _, policy, _, _ = release
    command, _, _ = signer
    public_key = tmp_path / "key.asc"
    public_key.write_bytes(subprocess.check_output(command + ["--armor", "--export"]))
    data = json.loads(policy.read_text())
    data["key_url"] = "https://keys.invalid/key.asc"
    policy.write_text(json.dumps(data))
    root = tmp_path / "root"
    rootfs.fetch(f"https://release.invalid/{archive.name}", root, tmp_path / "evidence")
    assert (root / "etc/os-release").is_file()


@pytest.mark.parametrize("failure", ["archive", "manifest", "untrusted", "absent-entry",
                                    "duplicate-entry", "bad-tar", "no-signature"])
def test_failure_never_populates_rootfs(tmp_path, release, failure):
    archive, manifest, signature, policy, keyring, sign = release
    if failure == "archive":
        archive.write_bytes(archive.read_bytes() + b"tampered")
    elif failure == "manifest":
        manifest.write_text(manifest.read_text().replace("*", " "))
    elif failure == "untrusted":
        policy.write_text(json.dumps({"primary_fingerprints": ["A" * 40]}))
    elif failure == "absent-entry":
        sign("0" * 64 + " *another-rootfs.tar.gz\n")
    elif failure == "duplicate-entry":
        sign(manifest.read_text() * 2)
    elif failure == "bad-tar":
        archive.write_bytes(b"signed checksum does not imply a valid tar archive")
        sign(hashlib.sha256(archive.read_bytes()).hexdigest() + f" *{archive.name}\n")
    else:
        signature.unlink()
    root = tmp_path / "root"
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "rootfs-verification.json").write_text('"stale-success"')
    with pytest.raises((ValueError, OSError, subprocess.SubprocessError)):
        rootfs.fetch(f"https://release.invalid/{archive.name}", root, evidence, keyring)
    assert not root.exists()
    assert not (evidence / "rootfs-verification.json").exists()
    assert not list(tmp_path.glob(".verified-rootfs-*"))


def test_existing_tree_is_not_overwritten(tmp_path, release):
    archive, _, _, _, keyring, _ = release
    root = tmp_path / "root"
    root.mkdir()
    (root / "user-data").write_text("keep")
    with pytest.raises(ValueError, match="empty directory"):
        rootfs.fetch(f"https://release.invalid/{archive.name}", root, tmp_path / "evidence", keyring)
    assert (root / "user-data").read_text() == "keep"


@pytest.mark.parametrize("url", ["http://release.invalid/base.tar.gz", "file:///tmp/base.tar.gz",
                                 "https://user:password@release.invalid/base.tar.gz"])
def test_download_rejects_insecure_or_credential_urls(tmp_path, url):
    with pytest.raises(ValueError):
        rootfs.download(url, tmp_path / "archive")


def test_wrong_signing_key_rejected_even_when_gpg_recognizes_it(tmp_path, release):
    _, manifest, signature, _, keyring, _ = release
    with pytest.raises(ValueError, match="pinned"):
        rootfs.verify_signature(manifest, signature, keyring, ["B" * 40], tmp_path / "verifier")


def test_builder_failure_diagnostics_never_chroot_into_unauthenticated_tree(tmp_path):
    commands = tmp_path / "commands"
    commands.mkdir()
    marker = tmp_path / "unsafe-command"
    for name, body in {"python3": "exit 1", "chroot": f"touch '{marker}'; exit 1",
                       "umount": f"touch '{marker}'; exit 1"}.items():
        command = commands / name
        command.write_text("#!/bin/sh\n" + body + "\n")
        command.chmod(0o755)
    work = tmp_path / "work"
    (work / "rootfs").mkdir(parents=True)
    evidence = tmp_path / "debug"
    env = dict(os.environ, PATH=str(commands) + os.pathsep + os.environ["PATH"],
               WORK=str(work), DEBUG_DIR=str(evidence))
    result = subprocess.run(["bash", str(REPO / "build/iso/build-iso.sh"), "full"],
                            cwd=tmp_path, env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode != 0
    assert not marker.exists(), "verification failure must not execute chroot or unmount an old tree"
    assert "chroot skipped" in (evidence / "environment.txt").read_text()
    assert "rootfs-auth\t1\t" in (evidence / "steps.tsv").read_text()
