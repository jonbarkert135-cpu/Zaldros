# SPDX-License-Identifier: GPL-3.0-or-later
"""Bootstrap failures must not overwrite user directories or install into global Python."""
import importlib.util
import os
from pathlib import Path
import sys
import venv

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "dev/setup.py"
spec = importlib.util.spec_from_file_location("development_setup", SCRIPT)
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


@pytest.fixture
def bare_venv(tmp_path):
    target = tmp_path / "environment"
    venv.EnvBuilder(with_pip=False).create(target)
    return target


def test_check_does_not_create_a_missing_environment(tmp_path, capsys):
    target = tmp_path / "absent"
    assert setup.main(["tools", "--venv", str(target), "--check"]) == 1
    assert not target.exists()
    assert "not an existing virtualenv" in capsys.readouterr().err


def test_check_rejects_missing_dependencies_without_installing(bare_venv, capsys):
    before = sorted(str(p.relative_to(bare_venv)) for p in bare_venv.rglob("*"))
    assert setup.main(["tools", "--venv", str(bare_venv), "--check"]) == 1
    assert "pytest" in capsys.readouterr().err
    assert before == sorted(str(p.relative_to(bare_venv)) for p in bare_venv.rglob("*"))


def test_existing_user_directory_is_preserved(tmp_path, capsys):
    target = tmp_path / "user-files"
    target.mkdir()
    sentinel = target / "document.txt"
    sentinel.write_text("keep this")
    assert setup.main(["tools", "--venv", str(target)]) == 1
    assert "non-venv" in capsys.readouterr().err
    assert sentinel.read_text() == "keep this"
    assert not (target / "pyvenv.cfg").exists()


def test_symlink_target_is_refused(tmp_path, capsys):
    destination = tmp_path / "destination"
    destination.mkdir()
    target = tmp_path / "symlink"
    target.symlink_to(destination, target_is_directory=True)
    assert setup.main(["tools", "--venv", str(target)]) == 1
    assert "symlink" in capsys.readouterr().err
    assert target.is_symlink() and not list(destination.iterdir())


def test_missing_python_fails_before_creating_target(tmp_path, capsys):
    target = tmp_path / "absent"
    assert setup.main(["tools", "--venv", str(target), "--python", str(tmp_path / "no-python")]) == 1
    assert "interpreter not found" in capsys.readouterr().err
    assert not target.exists()


def test_office_requires_uno_before_creating_target(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(setup, "required_commands", lambda _: None)
    def without_uno(*args, **kwargs):
        assert kwargs["modules"] == ["uno"]
        raise RuntimeError("UNO missing in selected interpreter")
    monkeypatch.setattr(setup, "probe", without_uno)
    target = tmp_path / "office"
    assert setup.main(["office", "--venv", str(target), "--python", sys.executable]) == 1
    assert "UNO missing" in capsys.readouterr().err
    assert not target.exists()


def test_shared_system_packages_are_refused_for_tools(bare_venv):
    config = bare_venv / "pyvenv.cfg"
    config.write_text(config.read_text().replace("include-system-site-packages = false",
                                                "include-system-site-packages = true"))
    with pytest.raises(RuntimeError, match="system-site-packages mode"):
        setup.validate_target("tools", bare_venv)


def test_global_interpreter_cannot_masquerade_as_target(bare_venv, monkeypatch):
    metadata = setup.probe(sys.executable)
    metadata.update(prefix=metadata["base_prefix"])
    monkeypatch.setattr(setup, "probe", lambda *args, **kwargs: metadata)
    with pytest.raises(RuntimeError, match="not isolated"):
        setup.validate_target("tools", bare_venv)


def test_a_base_prefix_alias_cannot_bypass_isolation(bare_venv, tmp_path, monkeypatch):
    alias = tmp_path / "base-alias"
    alias.symlink_to(bare_venv, target_is_directory=True)
    metadata = setup.probe(bare_venv / "bin/python")
    metadata["base_prefix"] = str(alias)
    monkeypatch.setattr(setup, "probe", lambda *args, **kwargs: metadata)
    with pytest.raises(RuntimeError, match="not isolated"):
        setup.validate_target("tools", bare_venv)


def test_different_base_interpreter_cannot_reuse_a_venv(bare_venv, monkeypatch):
    original = setup.probe
    def foreign_base(python, *args, **kwargs):
        data = original(python, *args, **kwargs)
        if str(python) == sys.executable:
            data["base_prefix"] = "/different/interpreter"
        return data
    monkeypatch.setattr(setup, "probe", foreign_base)
    with pytest.raises(RuntimeError, match="different base interpreter"):
        setup.prepare("tools", bare_venv, sys.executable)


def test_pip_installation_is_bound_to_validated_venv(bare_venv, monkeypatch):
    original = setup.subprocess.run
    installs = []
    def intercept(command, *args, **kwargs):
        if "pip" in command and "install" in command:
            installs.append(command)
            raise RuntimeError("stopped before installation")
        return original(command, *args, **kwargs)
    monkeypatch.setattr(setup.subprocess, "run", intercept)
    with pytest.raises(RuntimeError, match="stopped before installation"):
        setup.prepare("tools", bare_venv, sys.executable)
    assert len(installs) == 1
    assert installs[0][0] == str(bare_venv / "bin/python")
    assert "--require-virtualenv" in installs[0]


def test_wrong_dependency_version_cannot_report_ready(bare_venv, monkeypatch):
    original = setup.probe
    def wrong_version(python, packages=(), modules=()):
        data = original(python)
        data["packages"] = {"pytest": "0.0"} if packages else {}
        return data
    monkeypatch.setattr(setup, "probe", wrong_version)
    with pytest.raises(RuntimeError, match="dependency versions differ"):
        setup.check("tools", bare_venv)


def test_constraints_reject_duplicate_versions(tmp_path, monkeypatch):
    constraints = tmp_path / "constraints.txt"
    constraints.write_text("pytest==1.0\npytest==2.0\n")
    monkeypatch.setattr(setup, "CONSTRAINTS", constraints)
    with pytest.raises(RuntimeError, match="duplicate dependency pin"):
        setup.expected_versions("tools")


def test_child_environment_ignores_destination_overrides_without_changing_parent(monkeypatch):
    overrides = {"PIP_TARGET": "/outside/target", "PIP_PREFIX": "/outside/prefix",
                 "PIP_USER": "1", "PIP_LOG": "/outside/log", "PIP_CONSTRAINT": "/outside/constraints",
                 "PYTHONHOME": "/outside/python", "PYTHONPATH": "/outside/modules"}
    for key, value in overrides.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("PIP_CONFIG_FILE", "/outside/pip.conf")
    env = setup.child_environment()
    assert all(key not in env for key in overrides)
    assert env["PIP_CONFIG_FILE"] == os.devnull
    assert all(os.environ[key] == value for key, value in overrides.items())


def test_child_environment_keeps_network_configuration(monkeypatch):
    monkeypatch.setenv("PIP_INDEX_URL", "https://packages.example/simple")
    monkeypatch.setenv("PIP_CERT", "/trusted/ca.pem")
    monkeypatch.setenv("PIP_REQUIRE_HASHES", "1")
    env = setup.child_environment()
    assert env["PIP_INDEX_URL"] == "https://packages.example/simple"
    assert env["PIP_CERT"] == "/trusted/ca.pem"
    assert env["PIP_REQUIRE_HASHES"] == "1"
    assert env["PIP_REQUIRE_VIRTUALENV"] == "1"
