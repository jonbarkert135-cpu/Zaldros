# SPDX-License-Identifier: GPL-3.0-or-later
"""The report command must fail when an actual desktop acceptance step fails."""
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "build/iso/report.py"
spec = importlib.util.spec_from_file_location("functional_report", SCRIPT)
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)

GUEST = ("desktop_ready", "app_launch_explorer", "window_move", "minimize", "restore", "screenshot")
HOST = ("start_open", "start_close", "alt_tab", "task_view", "taskbar_response")


def result(**overrides):
    row = dict(variant="full", profile="modern", boot="PASS", kernel="7.0.0-test",
               systemd_state="running", failed_units="", pending_jobs="",
               wayland_socket=["/run/user/1000/wayland-0"], kwin=True, shell=True,
               app_launch={"started": True},
               ui_guest={"steps": {step: {"status": "PASS"} for step in GUEST}},
               ui_host={step: {"status": "PASS"} for step in HOST})
    # These are not duplicate measurements: the host owns the input injection.
    row["ui_guest"]["steps"].update({step: {"status": "BLOCKED"} for step in HOST})
    row["ui_guest"]["steps"]["frame_stability"] = {"status": "BLOCKED"}
    row.update(overrides)
    return row


def write(directory, row, name="boot.json"):
    (directory / name).write_text(json.dumps(row))
    return str(directory)


def test_complete_desktop_passes_with_host_owned_steps_and_unmeasured_frame_pacing(tmp_path):
    assert report.main(write(tmp_path, result())) == 0


def test_legacy_screenshot_failure_cannot_be_hidden_by_boot_pass(tmp_path, capsys):
    row = result(variant="legacy", profile="low")
    row["ui_guest"]["steps"]["screenshot"]["status"] = "FAIL"
    assert report.main(write(tmp_path, row)) == 1
    assert "screenshot" in capsys.readouterr().out


@pytest.mark.parametrize("step", GUEST + HOST)
def test_every_required_step_must_have_a_measurement_from_its_owner(tmp_path, step):
    row = result()
    source = row["ui_guest"]["steps"] if step in GUEST else row["ui_host"]
    del source[step]
    assert report.main(write(tmp_path, row)) == 1


@pytest.mark.parametrize("status", ["FAIL", "BLOCKED", "SKIPPED", "MISSING", "ERROR", "PASS with warnings"])
def test_only_an_actual_pass_satisfies_a_required_step(tmp_path, status):
    row = result()
    row["ui_host"]["alt_tab"]["status"] = status
    assert report.main(write(tmp_path, row)) == 1


def test_failure_from_other_observer_is_not_masked_by_owner_pass(tmp_path, capsys):
    row = result()
    row["ui_host"]["screenshot"] = {"status": "FAIL"}
    assert report.main(write(tmp_path, row)) == 1
    assert report.ui_cell(row, "screenshot").startswith("FAIL")


def test_pass_from_wrong_observer_cannot_replace_missing_owner(tmp_path):
    row = result()
    row["ui_guest"]["steps"]["start_open"] = {"status": "PASS"}
    del row["ui_host"]["start_open"]
    assert report.main(write(tmp_path, row)) == 1


def test_qmp_errors_fail_even_when_all_step_labels_claim_pass(tmp_path):
    row = result()
    row["ui_host"]["qmp_errors"] = ["input-send-event was rejected"]
    assert report.main(write(tmp_path, row)) == 1


def test_explicit_producer_failure_cannot_be_overruled_by_table_cells(tmp_path):
    row = result()
    row["checks"] = {"kernel": False}
    assert report.main(write(tmp_path, row)) == 1


def test_ui_report_level_failure_is_not_masked_by_successful_steps(tmp_path):
    row = result()
    row["ui_guest"]["status"] = "FAIL"
    assert report.main(write(tmp_path, row)) == 1


def test_pass_label_with_error_field_from_real_screenshot_bug_is_rejected(tmp_path):
    row = result()
    row["ui_guest"]["steps"]["screenshot"] = {
        "status": "PASS", "tool": "spectacle", "error": "the tool ran but wrote no file"}
    assert report.main(write(tmp_path, row)) == 1
    assert report.ui_cell(row, "screenshot").startswith("FAIL")


def test_failure_of_additional_measured_step_is_not_ignored(tmp_path):
    row = result()
    row["ui_guest"]["steps"]["frame_stability"] = {"status": "FAIL"}
    assert report.main(write(tmp_path, row)) == 1


def test_invalid_identity_reports_failure_instead_of_crashing(tmp_path):
    assert report.main(write(tmp_path, result(profile=[]))) == 1


@pytest.mark.parametrize("source", ["ui_guest", "ui_host"])
def test_missing_or_malformed_report_halves_fail_without_traceback(tmp_path, source):
    row = result()
    row[source] = ["malformed"]
    assert report.main(write(tmp_path, row)) == 1


def test_stale_target_does_not_validate_selected_job(tmp_path):
    assert report.main(write(tmp_path, result()), variant="legacy", profile="low") == 1


def test_duplicate_targets_fail_instead_of_counting_as_two_measurements(tmp_path):
    write(tmp_path, result())
    write(tmp_path, result(), "stale.json")
    assert report.main(str(tmp_path)) == 1


def test_one_failed_image_fails_the_combined_matrix(tmp_path):
    write(tmp_path, result())
    bad = result(variant="legacy", profile="low")
    bad["ui_guest"]["steps"]["screenshot"] = {"status": "FAIL"}
    write(tmp_path, bad, "legacy.json")
    assert report.main(str(tmp_path)) == 1


@pytest.mark.parametrize("overrides", [
    {"kernel": ""}, {"wayland_socket": []}, {"kwin": False}, {"shell": False},
    {"app_launch": {"started": False}}, {"failed_units": "bad.service loaded failed failed"},
    {"systemd_state": "starting", "pending_jobs": ""},
    {"systemd_state": "starting", "pending_jobs": "4 unrelated.service start running"},
    {"systemd_state": "starting", "pending_jobs": "4 fake-zaldros-selftest.service start running"},
    {"failed_checks": ["shell"]},
])
def test_boot_pass_label_cannot_override_failed_observed_facts(tmp_path, overrides):
    assert report.main(write(tmp_path, result(**overrides))) == 1


def test_own_selftest_pending_job_has_consistent_systemd_verdict(tmp_path, capsys):
    row = result(systemd_state="starting", pending_jobs="4 zaldros-selftest.service start running")
    assert report.main(write(tmp_path, row)) == 0
    assert "| PASS | PASS | PASS | PASS | PASS |" in capsys.readouterr().out


def test_malformed_json_returns_diagnostic_failure(tmp_path, capsys):
    (tmp_path / "boot.json").write_text('{"variant":')
    assert report.main(str(tmp_path)) == 1
    assert "boot.json" in capsys.readouterr().out


def test_command_exit_status_preserves_ui_failure(tmp_path):
    row = result()
    row["ui_host"]["taskbar_response"] = {"status": "FAIL"}
    write(tmp_path, row)
    done = subprocess.run([sys.executable, str(SCRIPT), str(tmp_path)], capture_output=True, text=True)
    assert done.returncode == 1


@pytest.mark.parametrize("screenshot,shell_running", [("PASS", True), ("FAIL", True), ("PASS", False)])
def test_actual_boot_script_composes_reports_with_the_same_gate(tmp_path, screenshot, shell_running):
    row = result(shell=shell_running)
    row["ui_guest"]["steps"]["screenshot"]["status"] = screenshot
    guest, host = row.pop("ui_guest"), row.pop("ui_host")
    path = tmp_path / "boot.json"
    path.write_text(json.dumps(row))
    (tmp_path / "boot.ui-guest.json").write_text(json.dumps(guest))
    (tmp_path / "boot-host.json").write_text(json.dumps(host))
    script = (REPO / "build/iso/boot-test.sh").read_text()
    body = re.search(r'python3 - "\$JSON"[^\n]+<<\'PY\'\n(.*?)\nPY', script, re.S)[1]
    done = subprocess.run([sys.executable, "-", str(path), "100", "modern", str(SCRIPT.parent)],
                          input=body, cwd=tmp_path, text=True, capture_output=True)
    assert done.returncode == (0 if shell_running else 1)
    composed = json.loads(path.read_text())
    assert composed["boot"] == ("PASS" if shell_running else "FAIL")
    assert composed["ui_guest"]["steps"]["screenshot"]["status"] == screenshot
    assert report.main(str(tmp_path), variant="full", profile="modern") == (
        0 if screenshot == "PASS" and shell_running else 1)
