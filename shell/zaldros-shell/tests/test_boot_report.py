"""Guard: the boot matrix must survive the shape the guest really reports.

iso run 33157358995 booted all nine images and every job was green — and the run summary held an
empty table. `build/iso/report.py` had crashed with
`AttributeError: 'dict' object has no attribute 'splitlines'`, because `boot_time` stopped being
the raw `systemd-analyze` text and became the two-way measurement dict from
`selftest.boot_seconds()`. The crash was invisible for a second reason: the step pipes the report
into `$GITHUB_STEP_SUMMARY` with `tee`, and without `pipefail` the pipeline exits 0 no matter what
Python did. Both halves are covered here, so the numbers cannot disappear silently again.

`pipefail` is checked in `docs/ci/iso.yml`; the live workflow under `.github/` has to be edited by
the owner, because Viktor's GitHub App is not allowed to push workflow files.
"""

import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
ISO = REPO / "build" / "iso"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ISO / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


report = _load("report")
selftest = _load("selftest")


def _result(**overrides):
    data = {
        "variant": "full", "profile": "modern", "boot": "PASS", "kernel": "6.14.0-zaldros",
        "systemd_state": "running", "wayland_socket": ["/run/user/1000/wayland-0"],
        "kwin": True, "shell": True, "app_launch": {"started": True},
        "mem_used_mib": 1462, "process_count": 214,
        "boot_time": {"uptime_at_selftest_s": 41.7, "systemd_analyze": None,
                      "kernel_s": None, "userspace_s": None},
    }
    data.update(overrides)
    return data


def _write(tmp_path, *results):
    for data in results:
        name = f"zaldros-{data['variant']}-{data['profile']}.json"
        (tmp_path / name).write_text(json.dumps(data))
    return tmp_path


def test_the_matrix_prints_the_boot_time_the_guest_actually_measures(tmp_path, capsys):
    code = report.main(str(_write(tmp_path, _result())))
    out = capsys.readouterr().out
    assert code == 0
    assert "| full | modern | PASS |" in out
    assert "41.7s to self-test" in out, "the uptime measurement must reach the table"
    assert "1462" in out and "214" in out


def test_kernel_and_userspace_are_preferred_when_systemd_analyze_answered(tmp_path, capsys):
    boot_time = {"uptime_at_selftest_s": 41.7, "systemd_analyze": "Startup finished in ...",
                 "kernel_s": 3.4, "userspace_s": 12.8}
    report.main(str(_write(tmp_path, _result(boot_time=boot_time))))
    assert "3.4s kernel + 12.8s userspace" in capsys.readouterr().out


@pytest.mark.parametrize("boot_time, expected", [
    ({"uptime_at_selftest_s": None}, "—"),                     # measured nothing, says nothing
    (None, "—"),                                               # the key never arrived
    ("Startup finished in 3.4s (kernel)\nnoise", "Startup finished in 3.4s (kernel)"),
])
def test_every_shape_of_boot_time_renders_instead_of_raising(boot_time, expected):
    assert report.boot_time_cell(boot_time) == expected


def test_the_column_handles_exactly_what_the_guest_produces():
    """Not a mock: the real function, run here, is what the column must swallow."""
    assert report.boot_time_cell(selftest.boot_seconds()) != ""


def test_a_failed_boot_still_returns_a_failing_exit_code(tmp_path, capsys):
    """The reason the step needs `pipefail`: this 1 is the only thing that says "did not boot"."""
    code = report.main(str(_write(tmp_path, _result(boot="FAIL", profile="low"))))
    capsys.readouterr()
    assert code == 1


def test_the_reviewed_workflow_does_not_swallow_the_report_exit_code():
    """`docs/ci/iso.yml` is the copy this repository reviews, so the gate is checked there.

    The live `.github/workflows/iso.yml` needs the same two lines. Viktor's GitHub App cannot
    push changes under `.github/workflows/` (`without workflows permission`), so applying them is
    an owner action — it is written down in TODO.md rather than quietly skipped here.
    """
    workflow = REPO / "docs" / "ci" / "iso.yml"
    text = workflow.read_text()
    assert "report.py results | tee" in text, workflow
    step = text.split("report.py results | tee")[0]
    assert "set -o pipefail" in step.rsplit("- name:", 1)[1], "tee hides a crash and an exit code"


# -- the UI drive's Alt+Tab verdict ----------------------------------------------------------------
ui_drive = _load("ui-drive") if (ISO / "ui-drive.py").is_file() else None


def test_a_held_frame_equal_to_the_release_frame_is_not_a_visible_switcher():
    """iso run 33158172265: alt_tab-held.png and alt_tab-after.png were byte-identical
    (md5 a4880e3e48) and the report still claimed `switcher_visible: true`. The window really did
    switch — our Explorer on top before, Dolphin on top after — but nothing proved an overlay."""
    verdict = ui_drive.alt_tab_verdict(showed=0.47488, overlay=0.0, switched=0.47488)
    assert verdict["status"] == "PASS", "the window changed; that is what the step is about"
    assert verdict["switched"] is True
    assert verdict["switcher_visible"] is False
    assert verdict["held_equals_after"] is True


def test_an_overlay_that_appears_and_vanishes_is_a_visible_switcher():
    verdict = ui_drive.alt_tab_verdict(showed=0.31, overlay=0.12, switched=0.47)
    assert verdict["switcher_visible"] is True and verdict["held_equals_after"] is False
    assert verdict["status"] == "PASS"


def test_a_screen_that_never_changed_fails_however_the_overlay_measured():
    verdict = ui_drive.alt_tab_verdict(showed=0.0, overlay=0.0, switched=0.0)
    assert verdict["status"] == "FAIL" and verdict["switched"] is False


def test_the_matrix_ignores_the_diagnostic_halves_next_to_a_boot_result(tmp_path):
    """iso run 33326841932: every boot job went red at "Result matrix" while the boot itself
    passed. `results/` had grown a `*.late.json` (the in-guest diagnostics), the report read it as
    an extra image and printed a `| ? | ? | FAIL |` row, which took the exit code to 1."""
    import json as _json

    (tmp_path / "zaldros-full-modern.json").write_text(_json.dumps(
        {"variant": "full", "profile": "modern", "boot": "PASS", "kernel": "7.0.0-30-generic",
         "systemd_state": "running", "wayland_socket": True, "kwin": True, "shell": True}))
    (tmp_path / "zaldros-full-modern.late.json").write_text(_json.dumps(
        {"switcher_script_lines": ["qml: ZALDROS-SWITCHER tabbox layout loaded"]}))
    (tmp_path / "zaldros-full-modern-host.json").write_text(_json.dumps({"alt_tab": {}}))
    # The build manifest also carries `variant`, so a row is "variant AND a boot verdict".
    (tmp_path / "zaldros-full.json").write_text(_json.dumps({"variant": "full", "size_mib": 2900}))

    report = _load("report")
    assert report.main(str(tmp_path)) == 0, "a passing boot next to its diagnostics is not a failure"
