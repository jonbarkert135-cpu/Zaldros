#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Prepare/check isolated development environments; never install system packages."""
from __future__ import annotations

import argparse
import configparser
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
CONSTRAINTS = ROOT / "tools/dev/constraints.txt"
PIP_SOURCE_OPTIONS = {
    "PIP_INDEX_URL", "PIP_EXTRA_INDEX_URL", "PIP_NO_INDEX", "PIP_FIND_LINKS",
    "PIP_TRUSTED_HOST", "PIP_CERT", "PIP_CLIENT_CERT", "PIP_PROXY",
    "PIP_TIMEOUT", "PIP_DEFAULT_TIMEOUT", "PIP_RETRIES", "PIP_REQUIRE_HASHES",
    "PIP_ONLY_BINARY", "PIP_NO_BINARY",
}
PROFILES = {
    "tools": (".venv-tools", "tools/dev/tools-requirements.txt", ["pytest"], ["pytest"]),
    "shell": (".venv", "tools/dev/shell-requirements.txt",
              ["pytest", "PySide6-Essentials", "Pillow", "numpy"],
              ["pytest", "PySide6.QtGui", "PySide6.QtQml", "PySide6.QtQuick", "PIL.Image", "numpy"]),
    "office": (".venv-office", "tools/ci/office-requirements.txt",
               ["pytest", "PySide6-Essentials"],
               ["pytest", "PySide6.QtGui", "PySide6.QtQml", "PySide6.QtQuick", "uno"]),
}
PROBE = """
import importlib, importlib.metadata, json, sys
packages, modules = json.loads(sys.argv[1])
loaded = {name: importlib.import_module(name) for name in modules}
print(json.dumps({
    'executable': sys.executable, 'prefix': sys.prefix, 'base_prefix': sys.base_prefix,
    'python': sys.version.split()[0], 'version_info': list(sys.version_info[:2]),
    'packages': {name: importlib.metadata.version(name) for name in packages},
    'uno_module': getattr(loaded.get('uno'), '__file__', None)}))
"""


def child_environment():
    # Destination/extra-requirement overrides must not escape the chosen venv.
    # Keep source/TLS/verification settings without echoing their secret values.
    inherited = {key: value for key, value in os.environ.items()
                 if key not in {"PYTHONPATH", "PYTHONHOME"}
                 and (not key.startswith("PIP_") or key in PIP_SOURCE_OPTIONS)}
    return {**inherited, "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1",
            "PIP_DISABLE_PIP_VERSION_CHECK": "1", "PIP_REQUIRE_VIRTUALENV": "1",
            "PIP_CONFIG_FILE": os.devnull}


def probe(python, packages=(), modules=()):
    done = subprocess.run([str(python), "-c", PROBE, json.dumps([packages, modules])],
                          capture_output=True, text=True, timeout=30, env=child_environment())
    if done.returncode:
        raise RuntimeError(f"interpreter probe failed: {done.stderr.strip()[-1800:]}")
    data = json.loads(done.stdout)
    if tuple(data["version_info"]) < (3, 12):
        raise RuntimeError("Python 3.12 or newer is required by the pinned development dependencies")
    return data


def required_commands(profile):
    commands = ("dbus-daemon", "gpg", "curl", "tar") if profile == "shell" else ()
    missing = [name for name in commands if not shutil.which(name)]
    if profile == "office" and not (shutil.which("soffice") or shutil.which("libreoffice")):
        missing.append("LibreOffice")
    if missing:
        raise RuntimeError(f"missing host dependencies: {', '.join(missing)}; see docs/development/SETUP.md")


def validate_target(profile, target):
    if target.is_symlink():
        raise RuntimeError("refusing a symlink as the virtualenv directory")
    config = target / "pyvenv.cfg"
    python = target / "bin/python"
    if not config.is_file() or not python.is_file():
        raise RuntimeError(f"not an existing virtualenv; refusing to overwrite: {target}")
    data = probe(python)
    if (Path(data["prefix"]).resolve() != target.resolve()
            or Path(data["prefix"]).resolve() == Path(data["base_prefix"]).resolve()):
        raise RuntimeError("target interpreter is not isolated in the requested virtualenv")
    settings = configparser.ConfigParser()
    settings.read_string("[venv]\n" + config.read_text())
    system_site = settings.getboolean("venv", "include-system-site-packages")
    if system_site != (profile == "office"):
        raise RuntimeError("virtualenv system-site-packages mode does not match the profile; choose a new directory")
    return python, data


def expected_versions(profile):
    # This owned file contains flat exact pins, not arbitrary pip requirement syntax.
    pins = {}
    for raw in CONSTRAINTS.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if not re.fullmatch(r"[A-Za-z0-9_.-]+==[A-Za-z0-9_.+-]+", line):
            raise RuntimeError(f"constraints must be flat exact pins: {line}")
        name, version = line.split("==")
        if name in pins:
            raise RuntimeError(f"duplicate dependency pin: {name}")
        pins[name] = version
    return {name: pins[name] for name in PROFILES[profile][2]}


def check(profile, target):
    required_commands(profile)
    python, _ = validate_target(profile, target)
    data = probe(python, PROFILES[profile][2], PROFILES[profile][3])
    expected = expected_versions(profile)
    if data["packages"] != expected:
        raise RuntimeError(f"dependency versions differ: expected {expected}, got {data['packages']}")
    return {"profile": profile, "readiness": "dependencies-imported", **data}


def prepare(profile, target, python):
    # Reject existing user directories before any installation can occur.
    if target.is_symlink():
        raise RuntimeError("refusing a symlink as the virtualenv directory")
    if target.exists() and not (target / "pyvenv.cfg").is_file():
        raise RuntimeError(f"refusing to overwrite a non-venv directory: {target}")
    required_commands(profile)
    selected = probe(python, modules=["uno"] if profile == "office" else [])
    if target.exists():
        _, current = validate_target(profile, target)
        if (current["version_info"] != selected["version_info"]
                or Path(current["base_prefix"]).resolve() != Path(selected["base_prefix"]).resolve()):
            raise RuntimeError("existing virtualenv uses a different base interpreter; choose a new directory")
    else:
        command = [str(python), "-m", "venv"]
        if profile == "office":
            command.append("--system-site-packages")
        subprocess.run([*command, str(target)], check=True, timeout=60, env=child_environment())
    target_python, _ = validate_target(profile, target)
    subprocess.run([str(target_python), "-m", "pip", "--require-virtualenv", "install",
                    "--no-cache-dir", "-r", str(ROOT / PROFILES[profile][1])],
                   check=True, timeout=600, env=child_environment())
    return check(profile, target)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", nargs="?", choices=PROFILES, default="shell")
    parser.add_argument("--venv", type=Path, help="default: profile-specific directory inside the repository")
    parser.add_argument("--python", help="creation interpreter; office defaults to /usr/bin/python3")
    parser.add_argument("--check", action="store_true", help="check an existing environment without installing")
    args = parser.parse_args(argv)
    target = (args.venv or ROOT / PROFILES[args.profile][0]).expanduser().absolute()
    try:
        if args.check:
            result = check(args.profile, target)
        else:
            requested = args.python or ("/usr/bin/python3" if args.profile == "office" else sys.executable)
            python = shutil.which(requested)
            if not python:
                raise RuntimeError(f"Python interpreter not found: {requested}")
            result = prepare(args.profile, target, python)
    except (OSError, ValueError, RuntimeError, KeyError, configparser.Error, subprocess.SubprocessError) as exc:
        print(f"Development setup FAIL: {exc}", file=sys.stderr)
        if args.profile == "office":
            print("Use the system Python matching python3-uno; see docs/office/BUILD.md.", file=sys.stderr)
        return 1
    encoded = json.dumps(result, sort_keys=True)
    if os.environ.get("GITHUB_ACTIONS") == "true":
        escaped = encoded.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
        print(f"\n::notice title=Development environment::{escaped}", file=sys.stderr, flush=True)
    print(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
