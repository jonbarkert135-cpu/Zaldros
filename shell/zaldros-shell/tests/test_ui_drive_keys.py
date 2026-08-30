"""The host key driver: every key name must exist, and QEMU's refusals must never be silent.

Run #36 (iso 33023389334) reported `alt_tab` FAIL for the sixth time. The cause was not KWin,
not kglobalaccel and not the keyboard layout — all three were cleared by the boot's own probes.
It was this driver: QKeyCode has no `alt_l` (left Alt is `alt`), so QEMU answered
`GenericError: Invalid parameter 'alt_l'` to every attempt to hold Alt, and `QMP.cmd` dropped
the reply on the floor. The guest received a bare Tab and the report blamed the system.

These tests make that class of bug impossible to ship twice: an unknown key name fails here, and
an error reply raises instead of vanishing.
"""

import importlib.util
import io
import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
ISO = REPO / "build" / "iso"
DRIVE_SRC = (ISO / "ui-drive.py").read_text()
SWITCHER_QML = (REPO / "system" / "theme" / "kwin-scripts" / "zaldros-switcher"
                / "contents" / "ui" / "main.qml").read_text()
INSTALLER = (REPO / "system" / "theme" / "install-visual-theme.sh").read_text()


def _load_drive():
    spec = importlib.util.spec_from_file_location("ui_drive", ISO / "ui-drive.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


drive = _load_drive()

# QKeyCode as QEMU defines it in qapi/ui.json — the modifiers are the part that bit us: there is
# no `alt_l`, `ctrl_l` or `shift_l`, while Meta really is `meta_l` / `meta_r`.
QKEYCODE = set("""
unmapped shift shift_r alt alt_r altgr altgr_r ctrl ctrl_r menu esc
1 2 3 4 5 6 7 8 9 0 minus equal backspace tab q w e r t y u i o p
bracket_left bracket_right ret a s d f g h j k l semicolon apostrophe grave_accent backslash
z x c v b n m comma dot slash asterisk spc caps_lock
f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 num_lock scroll_lock
kp_divide kp_multiply kp_subtract kp_add kp_enter kp_decimal sysrq
kp_0 kp_1 kp_2 kp_3 kp_4 kp_5 kp_6 kp_7 kp_8 kp_9 less f11 f12
print home pgup pgdn end left up down right insert delete stop again props undo front copy
open paste find cut lf help meta_l meta_r compose
""".split())


def key_names_used():
    """Every literal key name this driver hands to QEMU."""
    names = set()
    for call in re.findall(r"qmp\.key(?:_state)?\(([^)]*)\)", DRIVE_SRC):
        names.update(re.findall(r'"([a-z0-9_]+)"', call))
    for combo in drive.PROBE_KEYS.values():
        names.update(combo)
    return names


def test_the_driver_only_uses_key_names_qemu_knows():
    used = key_names_used()
    assert used, "no key names found — the parser, not the driver, is broken"
    assert used <= QKEYCODE, f"not QKeyCode names: {sorted(used - QKEYCODE)}"


def test_left_alt_is_called_alt():
    assert "alt_l" not in key_names_used()
    assert '"alt", True' in DRIVE_SRC


class FakeSocket:
    """Enough of a QMP endpoint to answer one command."""

    def __init__(self, reply, error_for="input-send-event"):
        self.written = []
        self._reply = reply + "\n"
        self._error_for = error_for
        self._lines = ['{"QMP": {}}\n', json.dumps({"return": {}}) + "\n"]

    def makefile(self, _mode):
        outer = self

        class File(io.StringIO):
            def readline(self, *_):
                if outer._lines:
                    return outer._lines.pop(0)
                last = outer.written[-1] if outer.written else ""
                if outer._error_for in last:
                    return outer._reply
                return json.dumps({"return": {}}) + "\n"

            def write(self, text):
                outer.written.append(text)
                return len(text)

            def flush(self):
                pass

        return File()


def qmp_with(reply, monkeypatch):
    monkeypatch.setattr(drive.socket, "socket", lambda *_: FakeSocket(reply))
    monkeypatch.setattr(FakeSocket, "connect", lambda self, path: None, raising=False)
    return drive.QMP("/nonexistent.qmp")


def test_an_error_reply_raises_and_is_recorded(monkeypatch):
    error = json.dumps({"error": {"class": "GenericError", "desc": "Invalid parameter 'alt_l'"}})
    qmp = qmp_with(error, monkeypatch)
    with pytest.raises(drive.QMPError) as caught:
        qmp.key_state("alt_l", True)
    assert "alt_l" in str(caught.value)
    assert qmp.errors and "alt_l" in qmp.errors[0]


def test_a_refused_key_fails_the_step_instead_of_measuring_pixels(monkeypatch, tmp_path):
    error = json.dumps({"error": {"class": "GenericError", "desc": "nope"}})
    qmp = qmp_with(error, monkeypatch)
    result = drive.timed_step(qmp, tmp_path, "start_open", lambda: qmp.key("meta_l"))
    assert result["status"] == "FAIL" and "nope" in result["qmp_error"]


def test_every_probe_the_driver_presses_exists_as_a_shortcut():
    """A probe is only evidence if the script registers it and the config seeds its key."""
    registered = dict(re.findall(r'name:\s*"([^"]+)"\s*\n\s*text:\s*"[^"]*"\s*\n\s*sequence:\s*"([^"]+)"',
                                 SWITCHER_QML))
    printed = set(re.findall(r'ZALDROS-PROBE ([a-z0-9_]+)"', SWITCHER_QML))
    # meta_tab is pressed too, but since run #40 it lands on the real fallback cycle (which logs
    # "cycle reverse=") instead of a printing probe, so it is not in `printed`.
    assert printed | {"meta_tab"} == set(drive.PROBE_KEYS), "driver and script disagree about the probes"
    for action, keys in (("Zaldros Probe Meta F9", "Meta+F9"),
                         ("Zaldros Probe Alt F9", "Alt+F9"),
                         ("Zaldros Probe Ctrl Shift F9", "Ctrl+Shift+F9"),
                         ("Zaldros Walk Through Windows", "Meta+Tab")):
        assert registered.get(action) == keys
        # unseeded actions are autoloaded as ",none," and cannot be pressed (run #35)
        assert f"{action}={keys},{keys}," in INSTALLER


def test_the_late_report_says_whether_a_key_ever_fired_the_switcher():
    selftest = (ISO / "selftest.py").read_text()
    assert '"probe_lines"' in selftest
    assert '"shortcut_fired_by_key"' in selftest


# --- Run #37: the key fired, and the driver still called it a failure ----------------------
#
# Boot 33108866212 answered the question the probes were built for: every one of the four probe
# shortcuts fired (`probe_lines` lists all four), `shortcut_fired_by_key` was true, `qmp_errors`
# was empty and the KWin script logged `cycle reverse=false candidates=1 / nothing to switch to`.
# Alt+Tab worked. It was pressed while the shell was the only window on screen, because the driver
# waited for ZALDROS-GEOMETRY — printed by the shell right after login — instead of for an
# application. These tests keep the driver honest about *when* it may measure Alt+Tab.


def test_the_driver_waits_for_a_real_second_window(tmp_path):
    serial = tmp_path / "serial.log"
    serial.write_text('ubuntu login: ZALDROS-GEOMETRY {"items": {"startButton": {"x": 1}}}\n')
    assert drive.second_window(serial) is None

    serial.write_text(serial.read_text()
                      + 'ZALDROS-WINDOWS-READY {"ready": true, "caption": "Home — Dolphin"}\n')
    found = drive.second_window(serial)
    assert found["ready"] is True and found["caption"] == "Home — Dolphin"


def test_an_escaped_copy_inside_an_embedded_log_is_not_mistaken_for_the_marker(tmp_path):
    """The late report embeds the session log, so escaped copies of markers travel with it."""
    serial = tmp_path / "serial.log"
    serial.write_text('ZALDROS-LATE {"tail": "ZALDROS-WINDOWS-READY {\\"ready\\": true}"}\n')
    assert drive.second_window(serial) is None


def test_without_a_second_window_alt_tab_is_blocked_not_failed(tmp_path, monkeypatch):
    serial = tmp_path / "serial.log"
    serial.write_text("nothing here\n")
    monkeypatch.setattr(drive.time, "sleep", lambda *_: None)
    assert drive.wait_for_second_window(serial, timeout=0) is None


def test_alt_tab_is_measured_only_after_the_guest_test_has_finished(tmp_path, monkeypatch):
    serial = tmp_path / "serial.log"
    serial.write_text("ZALDROS-UITEST {\"variant\": \"full\"}\n")
    monkeypatch.setattr(drive.time, "sleep", lambda *_: None)
    assert drive.wait_for_marker(serial, "ZALDROS-UITEST {", timeout=1) is not None
    assert drive.wait_for_marker(serial, "ZALDROS-NEVER {", timeout=0) is None


def test_the_guest_announces_the_second_window_before_it_starts_moving_it():
    uitest = (ISO / "uitest.py").read_text()
    ready = uitest.index("WINDOWS_MARK + json.dumps")
    assert ready < uitest.index('step("window_move"'), "the marker must precede the window ops"
    assert ready > uitest.index('step("app_launch_explorer"')


def test_the_late_report_quotes_what_the_switcher_did():
    selftest = (ISO / "selftest.py").read_text()
    assert '"switcher_cycles"' in selftest and '"alt_tab_switched"' in selftest
    # the switcher's verdict must be read before the D-Bus invoke fires one itself
    assert selftest.index('"alt_tab_switched"') < selftest.index('"invoke_delta"')
